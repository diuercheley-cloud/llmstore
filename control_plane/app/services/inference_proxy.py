import asyncio
from dataclasses import dataclass
import json
import logging
from time import perf_counter

import httpx
from fastapi import HTTPException, status
from starlette.responses import JSONResponse, StreamingResponse

from app.core.config import get_settings
from app.core.metrics import BACKEND_ERROR_COUNTER, BACKEND_LATENCY, REQUEST_COUNTER, REQUEST_LATENCY
from app.models.inference_backend import InferenceBackend
from app.services.circuit_breaker import CircuitBreaker, CircuitBreakerOpen
from app.services.queue_manager import QueueManager, QueueOverloaded, QueueTimeout
from app.utils.openai_response import normalize_chat_completion, normalize_chat_stream_line
from app.utils.token_estimator import estimate_tokens_from_text

logger = logging.getLogger(__name__)


@dataclass
class ForwardResult:
    response: JSONResponse | StreamingResponse
    backend_name: str
    attempts: int
    fallback_used: bool
    backend_errors: list[dict]


class InferenceProxy:
    def __init__(self, queue_manager: QueueManager, circuit_breaker: CircuitBreaker) -> None:
        settings = get_settings()
        self.settings = settings
        self.timeout = httpx.Timeout(settings.data_plane_timeout_seconds)
        self.attempt_timeout = httpx.Timeout(min(settings.data_plane_timeout_seconds, 20.0))
        self.clients: dict[str, httpx.AsyncClient] = {}
        self.queue_manager = queue_manager
        self.circuit_breaker = circuit_breaker

    def _get_client(self, base_url: str) -> httpx.AsyncClient:
        client = self.clients.get(base_url)
        if client is None:
            client = httpx.AsyncClient(base_url=base_url, timeout=self.timeout)
            self.clients[base_url] = client
        return client

    async def close(self) -> None:
        for client in self.clients.values():
            await client.aclose()
        self.clients.clear()

    async def health(self) -> bool:
        return await self.health_url(self.settings.data_plane_base_url, "/health")

    async def health_url(self, base_url: str, healthcheck_path: str) -> bool:
        try:
            response = await self._get_client(base_url).get(healthcheck_path)
            return response.status_code == 200
        except Exception:
            return False

    async def health_backend(self, backend: InferenceBackend) -> dict:
        started = perf_counter()
        ok = await self.health_url(backend.backend_url, backend.healthcheck_path)
        BACKEND_LATENCY.labels(backend_name=backend.name, endpoint="/health").observe(perf_counter() - started)
        return {
            "backend_id": str(backend.id),
            "name": backend.name,
            "provider": backend.provider,
            "backend_url": backend.backend_url,
            "max_parallel_requests": backend.max_parallel_requests,
            "current_running": backend.current_running,
            "ok": ok,
            "latency_ms": round((perf_counter() - started) * 1000, 2),
        }

    async def list_models(self, base_url: str | None = None) -> dict:
        try:
            await self.circuit_breaker.before_call()
            response = await self._get_client(base_url or self.settings.data_plane_base_url).get("/v1/models")
            response.raise_for_status()
            await self.circuit_breaker.record_success()
            return response.json()
        except (CircuitBreakerOpen, httpx.HTTPStatusError, httpx.TransportError) as exc:
            await self.circuit_breaker.record_failure()
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="data plane unavailable") from exc

    def _client_for_backend(self, backend: str, backend_url: str) -> httpx.AsyncClient:
        if backend not in {"llama.cpp", "ollama", "vllm"}:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="unsupported model backend")
        return self._get_client(backend_url)

    def _prepare_chat_payload(self, payload: dict, *, include_reasoning: bool, backend: str) -> dict:
        request_payload = dict(payload)
        if backend != "llama.cpp" or include_reasoning:
            return request_payload
        request_payload["reasoning_format"] = "none"
        template_kwargs = dict(request_payload.get("chat_template_kwargs") or {})
        template_kwargs["enable_thinking"] = False
        request_payload["chat_template_kwargs"] = template_kwargs
        return request_payload

    async def chat(
        self,
        payload: dict,
        stream: bool,
        include_reasoning: bool,
        backend: str,
        backend_url: str,
        backend_name: str,
        backend_id=None,
        manage_slot: bool = True,
    ):
        return await self._forward(
            "/v1/chat/completions",
            payload,
            stream,
            include_reasoning=include_reasoning,
            backend=backend,
            backend_url=backend_url,
            backend_name=backend_name,
            backend_id=backend_id,
            manage_slot=manage_slot,
        )

    async def complete(
        self,
        payload: dict,
        stream: bool,
        backend: str,
        backend_url: str,
        backend_name: str,
        backend_id=None,
        manage_slot: bool = True,
    ):
        return await self._forward(
            "/v1/completions",
            payload,
            stream,
            backend=backend,
            backend_url=backend_url,
            backend_name=backend_name,
            backend_id=backend_id,
            manage_slot=manage_slot,
        )

    async def _forward(
        self,
        endpoint: str,
        payload: dict,
        stream: bool,
        include_reasoning: bool = False,
        backend: str = "llama.cpp",
        backend_url: str | None = None,
        backend_name: str = "",
        backend_id=None,
        manage_slot: bool = True,
    ):
        try:
            await self.circuit_breaker.before_call()
            if manage_slot:
                async with self.queue_manager.slot(backend_id=backend_id):
                    if stream:
                        return await self._streaming_forward(
                            endpoint,
                            payload,
                            include_reasoning=include_reasoning,
                            backend=backend,
                            backend_url=backend_url or self.settings.data_plane_base_url,
                            backend_name=backend_name,
                        )
                    return await self._json_forward(
                        endpoint,
                        payload,
                        include_reasoning=include_reasoning,
                        backend=backend,
                        backend_url=backend_url or self.settings.data_plane_base_url,
                        backend_name=backend_name,
                    )
            if stream:
                return await self._streaming_forward(
                    endpoint,
                    payload,
                    include_reasoning=include_reasoning,
                    backend=backend,
                    backend_url=backend_url or self.settings.data_plane_base_url,
                    backend_name=backend_name,
                )
            return await self._json_forward(
                endpoint,
                payload,
                include_reasoning=include_reasoning,
                backend=backend,
                backend_url=backend_url or self.settings.data_plane_base_url,
                backend_name=backend_name,
            )
        except CircuitBreakerOpen as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
        except QueueOverloaded as exc:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc
        except QueueTimeout as exc:
            raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=str(exc)) from exc

    async def _json_forward(
        self,
        endpoint: str,
        payload: dict,
        include_reasoning: bool = False,
        backend: str = "llama.cpp",
        backend_url: str = "",
        backend_name: str = "",
    ) -> JSONResponse:
        started = perf_counter()
        last_error: Exception | None = None
        client = self._client_for_backend(backend, backend_url)
        target_endpoint = endpoint
        request_payload = self._prepare_chat_payload(payload, include_reasoning=include_reasoning, backend=backend)
        if backend == "ollama":
            target_endpoint, request_payload = self._translate_ollama_request(endpoint, payload, stream=False)
        for attempt in range(1, self.settings.retry_attempts + 2):
            try:
                response = await client.post(target_endpoint, json=request_payload, timeout=self.attempt_timeout)
                response.raise_for_status()
                await self.circuit_breaker.record_success()
                REQUEST_COUNTER.labels(endpoint=endpoint, status="success").inc()
                REQUEST_LATENCY.labels(endpoint=endpoint).observe(perf_counter() - started)
                BACKEND_LATENCY.labels(backend_name=backend_name or backend, endpoint=endpoint).observe(perf_counter() - started)
                response_payload = response.json()
                if backend == "ollama":
                    response_payload = self._translate_ollama_response(response_payload, endpoint, payload.get("model", ""))
                if endpoint == "/v1/chat/completions":
                    response_payload = normalize_chat_completion(response_payload, include_reasoning=include_reasoning)
                return ForwardResult(
                    response=JSONResponse(status_code=response.status_code, content=response_payload),
                    backend_name=backend_name,
                    attempts=1,
                    fallback_used=False,
                    backend_errors=[],
                )
            except (httpx.HTTPStatusError, httpx.TransportError) as exc:
                last_error = exc
                retriable = isinstance(exc, httpx.TransportError) or getattr(exc.response, "status_code", 500) >= 500
                if attempt > self.settings.retry_attempts or not retriable:
                    break
                await asyncio.sleep(self.settings.retry_backoff_seconds * attempt)
        await self.circuit_breaker.record_failure()
        REQUEST_COUNTER.labels(endpoint=endpoint, status="error").inc()
        BACKEND_ERROR_COUNTER.labels(
            backend_name=backend_name or backend,
            endpoint=endpoint,
            status_code=str(getattr(getattr(last_error, "response", None), "status_code", 503)),
        ).inc()
        logger.warning("data plane request failed", extra={"extra_data": {"endpoint": endpoint, "error": str(last_error)}})
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="data plane unavailable")

    async def _streaming_forward(
        self,
        endpoint: str,
        payload: dict,
        include_reasoning: bool = False,
        backend: str = "llama.cpp",
        backend_url: str = "",
        backend_name: str = "",
    ) -> StreamingResponse:
        started = perf_counter()
        client = self._client_for_backend(backend, backend_url)
        target_endpoint = endpoint
        request_payload = self._prepare_chat_payload(payload, include_reasoning=include_reasoning, backend=backend)
        if backend == "ollama":
            target_endpoint, request_payload = self._translate_ollama_request(endpoint, payload, stream=True)
        stream_client = httpx.AsyncClient(base_url=backend_url, timeout=self.attempt_timeout)
        request = stream_client.build_request("POST", target_endpoint, json=request_payload)
        try:
            response = await stream_client.send(request, stream=True)
            response.raise_for_status()
            await self.circuit_breaker.record_success()
            BACKEND_LATENCY.labels(backend_name=backend_name or backend, endpoint=endpoint).observe(perf_counter() - started)
        except (httpx.HTTPStatusError, httpx.TransportError) as exc:
            await stream_client.aclose()
            await self.circuit_breaker.record_failure()
            REQUEST_COUNTER.labels(endpoint=endpoint, status="error").inc()
            BACKEND_ERROR_COUNTER.labels(
                backend_name=backend_name or backend,
                endpoint=endpoint,
                status_code=str(getattr(getattr(exc, "response", None), "status_code", 503)),
            ).inc()
            logger.warning(
                "data plane stream setup failed",
                extra={"extra_data": {"endpoint": endpoint, "backend_name": backend_name, "error": str(exc)}},
            )
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="data plane unavailable") from exc

        async def event_stream():
            completion_fragments: list[str] = []
            try:
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    if backend == "ollama":
                        translated_line = self._translate_ollama_stream_line(line, endpoint, payload.get("model", ""))
                        if translated_line is None:
                            continue
                        line = translated_line
                    if line.startswith("data: ") and line != "data: [DONE]":
                        try:
                            parsed = json.loads(line.removeprefix("data: "))
                            delta = (
                                parsed.get("choices", [{}])[0]
                                .get("delta", {})
                                .get("content", "")
                                or parsed.get("choices", [{}])[0].get("text", "")
                            )
                            completion_fragments.append(delta)
                        except json.JSONDecodeError:
                            pass
                    if endpoint == "/v1/chat/completions":
                        normalized_line = normalize_chat_stream_line(line, include_reasoning=include_reasoning)
                        if normalized_line is None:
                            continue
                        yield f"{normalized_line}\n\n"
                        continue
                    yield f"{line}\n\n"
            except (httpx.HTTPStatusError, httpx.TransportError) as exc:
                await self.circuit_breaker.record_failure()
                error_event = {"error": {"message": "stream interrupted", "type": exc.__class__.__name__}}
                yield f"data: {json.dumps(error_event)}\n\n"
            finally:
                await response.aclose()
                await stream_client.aclose()
                REQUEST_COUNTER.labels(endpoint=endpoint, status="success").inc()
                REQUEST_LATENCY.labels(endpoint=endpoint).observe(perf_counter() - started)
                logger.info(
                    "stream completed",
                    extra={"extra_data": {"endpoint": endpoint, "completion_tokens_estimated": estimate_tokens_from_text(''.join(completion_fragments))}},
                )

        return ForwardResult(
            response=StreamingResponse(event_stream(), media_type="text/event-stream"),
            backend_name=backend_name,
            attempts=1,
            fallback_used=False,
            backend_errors=[],
        )

    def _translate_ollama_request(self, endpoint: str, payload: dict, stream: bool) -> tuple[str, dict]:
        if endpoint == "/v1/chat/completions":
            return "/api/chat", {
                "model": payload["model"],
                "messages": payload.get("messages", []),
                "stream": stream,
                "options": {
                    "temperature": payload.get("temperature"),
                    "top_p": payload.get("top_p"),
                    "num_predict": payload.get("max_tokens"),
                },
            }
        return "/api/generate", {
            "model": payload["model"],
            "prompt": payload.get("prompt", ""),
            "stream": stream,
            "options": {
                "temperature": payload.get("temperature"),
                "top_p": payload.get("top_p"),
                "num_predict": payload.get("max_tokens"),
            },
        }

    def _translate_ollama_response(self, payload: dict, endpoint: str, model_name: str) -> dict:
        if endpoint == "/v1/chat/completions":
            content = ((payload.get("message") or {}).get("content")) or payload.get("response", "")
            return {
                "id": f"chatcmpl-ollama-{model_name}",
                "object": "chat.completion",
                "created": int(perf_counter()),
                "model": model_name,
                "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": content}}],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            }
        return {
            "id": f"cmpl-ollama-{model_name}",
            "object": "text_completion",
            "created": int(perf_counter()),
            "model": model_name,
            "choices": [{"index": 0, "finish_reason": "stop", "text": payload.get("response", "")}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }

    def _translate_ollama_stream_line(self, line: str, endpoint: str, model_name: str) -> str | None:
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            return None
        if endpoint == "/v1/chat/completions":
            delta = ((payload.get("message") or {}).get("content")) or ""
            chunk = {
                "id": f"chatcmpl-ollama-{model_name}",
                "object": "chat.completion.chunk",
                "created": int(perf_counter()),
                "model": model_name,
                "choices": [{"index": 0, "delta": {"content": delta}, "finish_reason": None}],
            }
            return f"data: {json.dumps(chunk)}"
        chunk = {
            "id": f"cmpl-ollama-{model_name}",
            "object": "text_completion",
            "created": int(perf_counter()),
            "model": model_name,
            "choices": [{"index": 0, "text": payload.get('response', ''), "finish_reason": None}],
        }
        return f"data: {json.dumps(chunk)}"
