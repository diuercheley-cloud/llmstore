import asyncio
import json
import logging
import uuid
from dataclasses import dataclass
from functools import lru_cache
from time import perf_counter

import httpx
from app.core.config import get_settings
from app.core.metrics import (
    BACKEND_ERROR_COUNTER,
    BACKEND_LATENCY,
    REQUEST_COUNTER,
    REQUEST_LATENCY,
    record_backend_error,
    record_inference_latency,
    record_model_error,
)
from app.models.core.inference_backend import InferenceBackend
from app.services.circuit_breaker import CircuitBreaker, CircuitBreakerOpen
from app.services.context_manager import get_context_manager
from app.services.queue_manager import QueueOverloaded, QueueTimeout
from app.utils.anti_loop import detect_repetition, truncate_at_repetition
from app.utils.model_prompting import apply_prompt_template_settings
from app.utils.openai_response import normalize_chat_completion, normalize_chat_stream_line
from app.utils.tool_calling import sanitize_tool_calls
from fastapi import HTTPException, status
from starlette.responses import JSONResponse, StreamingResponse

logger = logging.getLogger(__name__)


@dataclass
class ForwardResult:
    response: JSONResponse | StreamingResponse
    backend_name: str
    attempts: int
    fallback_used: bool
    backend_errors: list[dict]
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    tokenizer_used: str = "fallback"
    real_fallback_used: bool = True



from app.contracts.queue import QueueContract


class InferenceProxy:
    def __init__(self, queue_manager: QueueContract, circuit_breaker: CircuitBreaker) -> None:
        settings = get_settings()
        self.settings = settings
        self.timeout = httpx.Timeout(settings.data_plane_timeout_seconds)
        self.attempt_timeout = httpx.Timeout(settings.data_plane_timeout_seconds)
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
        health_path = backend.healthcheck_path
        
        # Auto-detect health path if default /health fails for openai_compatible
        ok = await self.health_url(backend.backend_url, health_path)
        if not ok and backend.provider in ("openai_compatible", "vllm") and health_path == "/health":
            # Try /v1/models as a fallback health check for OpenAI-compatible/vLLM backends
            ok = await self.health_url(backend.backend_url, "/v1/models")
            if ok:
                health_path = "/v1/models"
            else:
                # Try /models
                ok = await self.health_url(backend.backend_url, "/models")
                if ok:
                    health_path = "/models"

        BACKEND_LATENCY.labels(backend_name=backend.name, endpoint=health_path).observe(perf_counter() - started)
        return {
            "backend_id": str(backend.id),
            "name": backend.name,
            "provider": backend.provider,
            "backend_url": backend.backend_url,
            "healthcheck_path": health_path,
            "max_parallel_requests": backend.max_parallel_requests,
            "current_running": backend.current_running,
            "ok": ok,
            "latency_ms": round((perf_counter() - started) * 1000, 2),
        }

    async def list_models(self, base_url: str | None = None, api_key: str | None = None) -> dict:
        target_url = base_url or self.settings.data_plane_base_url
        client = self._get_client(target_url)
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
            
        try:
            await self.circuit_breaker.before_call()
            # Try /v1/models first
            response = await client.get("/v1/models", headers=headers)
            if response.status_code == 404:
                # Fallback to /models
                response = await client.get("/models", headers=headers)
            
            response.raise_for_status()
            await self.circuit_breaker.record_success()
            return response.json()
        except (CircuitBreakerOpen, httpx.HTTPStatusError, httpx.TransportError) as exc:
            if self._should_trip_circuit_breaker(exc):
                await self.circuit_breaker.record_failure()
                raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="backend unavailable") from exc
            if isinstance(exc, httpx.HTTPStatusError):
                raise HTTPException(status_code=exc.response.status_code, detail=self._backend_error_detail(exc)) from exc
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="backend unavailable") from exc

    def _client_for_backend(self, backend: str, backend_url: str) -> httpx.AsyncClient:
        if backend not in {"llama.cpp", "ollama", "vllm", "tgi", "openai_compatible", "openrouter", "openai", "anthropic", "deepseek", "lmstudio"}:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="unsupported model backend")
        return self._get_client(backend_url)

    def _should_trip_circuit_breaker(self, exc: Exception) -> bool:
        if isinstance(exc, httpx.TransportError):
            return True
        if isinstance(exc, httpx.HTTPStatusError):
            return exc.response.status_code >= 500
        return False

    def _backend_error_detail(self, exc: httpx.HTTPStatusError | httpx.TransportError) -> object:
        if isinstance(exc, httpx.HTTPStatusError):
            try:
                backend_response = exc.response.json()
            except Exception:
                backend_response = exc.response.reason_phrase
            return {
                "message": "data plane rejected request",
                "backend_status_code": exc.response.status_code,
                "backend_response": backend_response,
            }
        return "data plane unavailable"


@lru_cache
def get_inference_proxy() -> "InferenceProxy":
    from app.services.backend_slot_manager import BackendSlotManager
    from app.services.queue_manager import QueueManager

    queue_manager = QueueManager(BackendSlotManager())
    circuit_breaker = CircuitBreaker()
    return InferenceProxy(queue_manager, circuit_breaker)

    def _normalize_openrouter_endpoint(self, backend_url: str, endpoint: str) -> str:
        normalized_url = (backend_url or "").rstrip("/")
        if not endpoint.startswith("/v1/"):
            return endpoint
        if normalized_url.endswith("/api/v1"):
            return endpoint.removeprefix("/v1")
        if normalized_url.endswith("/api"):
            return endpoint
        return "/api" + endpoint

    async def _prepare_chat_payload(
        self,
        payload: dict,
        *,
        include_reasoning: bool,
        backend: str,
        prompt_template: str | None = None,
    ) -> dict:
        updated = dict(payload)
        messages = updated.get("messages")
        if isinstance(messages, list) and messages:
            from app.contracts.token_accounting import TokenAccountingContract
            from app.services.tokenizer_service import get_tokenizer_service
            tokenizer: TokenAccountingContract = get_tokenizer_service()
            context_manager = get_context_manager()
            trimmed_messages, capped_max_tokens, metrics = await context_manager.manage(
                messages=[m for m in messages if isinstance(m, dict)],
                requested_max_tokens=updated.get("max_tokens"),
                model_id=str(updated.get("model") or ""),
                tokenizer=tokenizer,
            )
            if metrics.get("truncated") or trimmed_messages != messages:
                updated["messages"] = trimmed_messages
                if updated.get("max_tokens") != capped_max_tokens:
                    updated["max_tokens"] = capped_max_tokens
        return apply_prompt_template_settings(
            updated,
            prompt_template=prompt_template,
            include_reasoning=include_reasoning,
            backend=backend,
        )

    def _chat_response_has_visible_output(self, payload: dict, *, include_reasoning: bool) -> bool:
        for choice in payload.get("choices", []):
            if not isinstance(choice, dict):
                continue
            message = choice.get("message") or {}
            if not isinstance(message, dict):
                continue
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                return True
            tool_calls = message.get("tool_calls")
            if isinstance(tool_calls, list) and tool_calls:
                return True
            if include_reasoning:
                reasoning = message.get("reasoning_content") or message.get("reasoning")
                if isinstance(reasoning, str) and reasoning.strip():
                    return True
        return False

    def _validate_chat_response_payload(
        self,
        payload: dict,
        *,
        include_reasoning: bool,
        backend_name: str,
    ) -> None:
        if self._chat_response_has_visible_output(payload, include_reasoning=include_reasoning):
            return
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": f"backend '{backend_name}' returned empty or invalid chat completion. Verify if the model '{payload.get('model')}' is loaded and supports chat.",
                "backend_name": backend_name,
                "model_requested": payload.get("model"),
            },
        )

    def _sanitize_logged_payload(self, payload: dict) -> dict:
        logged_payload = dict(payload)
        if "messages" in logged_payload:
            logged_payload["messages"] = [
                {
                    "role": m.get("role"), 
                    "content_len": len(str(m.get("content") or "")),
                    "reasoning_len": len(str(m.get("reasoning_content") or m.get("reasoning") or ""))
                }
                for m in logged_payload["messages"]
            ]
        if "tools" in logged_payload and isinstance(logged_payload["tools"], list):
            logged_payload["tools"] = [
                (item.get("function") or {}).get("name") or item.get("type") or "unknown"
                for item in logged_payload["tools"]
                if isinstance(item, dict)
            ]
        if "tool_choice" in logged_payload and isinstance(logged_payload["tool_choice"], dict):
            logged_payload["tool_choice"] = {
                "type": logged_payload["tool_choice"].get("type"),
                "function": {"name": (logged_payload["tool_choice"].get("function") or {}).get("name")},
            }
        return logged_payload

    async def chat(
        self,
        payload: dict,
        stream: bool,
        include_reasoning: bool,
        backend: str,
        backend_url: str,
        backend_name: str,
        backend_id=None,
        prompt_template: str | None = None,
        manage_slot: bool = True,
        api_key: str | None = None,
        plan_code: str = "free",
        is_admin: bool = False,
    ):
        logger.debug(
            "inference proxy chat started",
            extra={
                "extra_data": {
                    "model_requested": payload.get("model"),
                    "backend_selected": backend_name or backend,
                    "stream": stream,
                    "prompt_template": prompt_template,
                    "plan_code": plan_code,
                    "is_admin": is_admin,
                }
            },
        )
        return await self._forward(
            "/v1/chat/completions",
            payload,
            stream,
            include_reasoning=include_reasoning,
            backend=backend,
            backend_url=backend_url,
            backend_name=backend_name,
            backend_id=backend_id,
            prompt_template=prompt_template,
            manage_slot=manage_slot,
            api_key=api_key,
            plan_code=plan_code,
            is_admin=is_admin,
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
        api_key: str | None = None,
        plan_code: str = "free",
        is_admin: bool = False,
    ):
        logger.debug(
            "inference proxy completion started",
            extra={
                "extra_data": {
                    "model_requested": payload.get("model"),
                    "backend_selected": backend_name or backend,
                    "stream": stream,
                    "plan_code": plan_code,
                    "is_admin": is_admin,
                }
            },
        )
        return await self._forward(
            "/v1/completions",
            payload,
            stream,
            backend=backend,
            backend_url=backend_url,
            backend_name=backend_name,
            backend_id=backend_id,
            manage_slot=manage_slot,
            api_key=api_key,
            plan_code=plan_code,
            is_admin=is_admin,
        )

    async def embeddings(
        self,
        payload: dict,
        backend: str,
        backend_url: str,
        backend_name: str,
        backend_id=None,
        api_key: str | None = None,
        plan_code: str = "free",
        is_admin: bool = False,
    ):
        logger.debug(
            "inference proxy embeddings started",
            extra={
                "extra_data": {
                    "model_requested": payload.get("model"),
                    "backend_selected": backend_name or backend,
                    "plan_code": plan_code,
                    "is_admin": is_admin,
                }
            },
        )
        return await self._forward(
            "/v1/embeddings",
            payload,
            stream=False,
            backend=backend,
            backend_url=backend_url,
            backend_name=backend_name,
            backend_id=backend_id,
            manage_slot=True,
            api_key=api_key,
            plan_code=plan_code,
            is_admin=is_admin,
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
        prompt_template: str | None = None,
        manage_slot: bool = True,
        api_key: str | None = None,
        plan_code: str = "free",
        is_admin: bool = False,
    ):
        from app.services.chaos.injection import inject_chaos
        # Chaos Injection: Data Plane Latency
        await inject_chaos("data_plane_latency")

        # Chaos Injection: Provider Timeout
        try:
            await inject_chaos("provider_timeout")
        except asyncio.TimeoutError:
            raise httpx.ReadTimeout("Simulated chaos provider timeout", request=None)
        except Exception as e:
            if "timeout" in str(e).lower():
                raise httpx.ReadTimeout(str(e), request=None)
            raise

        try:
            await self.circuit_breaker.before_call()
            if manage_slot:
                async with self.queue_manager.slot(plan_code=plan_code, is_admin=is_admin, backend_id=backend_id):
                    if stream:
                        return await self._streaming_forward(
                            endpoint,
                            payload,
                            include_reasoning=include_reasoning,
                            backend=backend,
                            backend_url=backend_url or self.settings.data_plane_base_url,
                            backend_name=backend_name,
                            prompt_template=prompt_template,
                            api_key=api_key,
                            plan_code=plan_code,
                        )
                    return await self._json_forward(
                        endpoint,
                        payload,
                        include_reasoning=include_reasoning,
                        backend=backend,
                        backend_url=backend_url or self.settings.data_plane_base_url,
                        backend_name=backend_name,
                        prompt_template=prompt_template,
                        api_key=api_key,
                        plan_code=plan_code,
                    )
            if stream:
                return await self._streaming_forward(
                    endpoint,
                    payload,
                    include_reasoning=include_reasoning,
                    backend=backend,
                    backend_url=backend_url or self.settings.data_plane_base_url,
                    backend_name=backend_name,
                    prompt_template=prompt_template,
                    api_key=api_key,
                    plan_code=plan_code,
                )
            return await self._json_forward(
                endpoint,
                payload,
                include_reasoning=include_reasoning,
                backend=backend,
                backend_url=backend_url or self.settings.data_plane_base_url,
                backend_name=backend_name,
                prompt_template=prompt_template,
                api_key=api_key,
                plan_code=plan_code,
            )
        except CircuitBreakerOpen as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
        except QueueOverloaded as exc:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": str(exc),
                    "queue": getattr(exc, "queue_name", "unknown"),
                    "retry_after": 5,
                    "request_id": str(uuid.uuid4()),
                }
            ) from exc
        except QueueTimeout as exc:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail={
                    "error": str(exc),
                    "queue": getattr(exc, "queue_name", "unknown"),
                    "retry_after": 2,
                    "request_id": str(uuid.uuid4()),
                }
            ) from exc

    async def _json_forward(
        self,
        endpoint: str,
        payload: dict,
        include_reasoning: bool = False,
        backend: str = "llama.cpp",
        backend_url: str = "",
        backend_name: str = "",
        prompt_template: str | None = None,
        api_key: str | None = None,
        plan_code: str = "free",
    ) -> JSONResponse:
        started = perf_counter()
        last_error: Exception | None = None
        client = self._client_for_backend(backend, backend_url)
        
        # Ensure endpoint starts with /v1/ if it's chat/completions/embeddings and not already there
        target_endpoint = endpoint
        if not target_endpoint.startswith("/v1/") and any(t in target_endpoint for t in ["chat/completions", "completions", "embeddings"]):
            target_endpoint = f"/v1/{target_endpoint.lstrip('/')}"
        
        if backend == "openrouter" and target_endpoint.startswith("/v1/"):
            target_endpoint = self._normalize_openrouter_endpoint(backend_url, target_endpoint)
        request_payload = await self._prepare_chat_payload(
            payload,
            include_reasoning=include_reasoning,
            backend=backend,
            prompt_template=prompt_template,
        )
        if backend == "ollama":
            target_endpoint, request_payload = self._translate_ollama_request(endpoint, payload, stream=False)

        # Real token counting: count prompt tokens before call
        from app.services.token_counting.token_counter import TokenCounter
        token_counter = TokenCounter()

        model_name = request_payload.get("model") or payload.get("model") or ""
        messages = request_payload.get("messages") or request_payload.get("prompt") or payload.get("messages") or payload.get("prompt") or ""

        real_prompt_tokens = 0
        tokenizer_used = "fallback"
        fallback_used = True
        try:
            counting_res = token_counter.count_tokens(messages, "", model_name, provider=backend)
            real_prompt_tokens = counting_res.prompt_tokens
            tokenizer_used = counting_res.tokenizer_used
            fallback_used = counting_res.fallback_used
        except Exception as e:
            logger.warning(f"Error counting prompt tokens: {e}")


        # Secure debug log for payload
        logged_payload = self._sanitize_logged_payload(request_payload)
        logger.info(
            "forwarding request to data plane",
            extra={
                "extra_data": {
                    "endpoint": target_endpoint,
                    "payload": logged_payload,
                    "backend_url": backend_url,
                    "effective_params": {
                        "max_tokens": request_payload.get("max_tokens"),
                        "n_predict": request_payload.get("n_predict"),
                        "temperature": request_payload.get("temperature"),
                        "stop": request_payload.get("stop"),
                        "stream": request_payload.get("stream"),
                    }
                }
            },
        )

        for attempt in range(1, self.settings.retry_attempts + 2):
            try:
                headers = {
                    "HTTP-Referer": "https://github.com/google/gemini-cli",
                    "X-Title": "Gemini CLI",
                }
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"
                elif backend_name == "lmstudio-local" and self.settings.lmstudio_api_key:
                    headers["Authorization"] = f"Bearer {self.settings.lmstudio_api_key}"
                
                logger.info(f"Forwarding to {client.base_url}{target_endpoint} with headers keys: {list(headers.keys())}")
                response = await client.post(target_endpoint, json=request_payload, headers=headers, timeout=self.attempt_timeout)
                response.raise_for_status()
                await self.circuit_breaker.record_success()
                REQUEST_COUNTER.labels(endpoint=endpoint, status="success").inc()
                elapsed = perf_counter() - started
                REQUEST_LATENCY.labels(endpoint=endpoint).observe(elapsed)
                BACKEND_LATENCY.labels(backend_name=backend_name or backend, endpoint=endpoint).observe(elapsed)
                record_inference_latency(
                    model=payload.get("model"),
                    backend=backend_name or backend,
                    plan=plan_code,
                    endpoint=endpoint,
                    status_code=response.status_code,
                    latency_seconds=elapsed,
                )
                response_payload = response.json()
                if backend == "ollama":
                    response_payload = self._translate_ollama_response(response_payload, endpoint, payload.get("model", ""))
                
                if endpoint == "/v1/chat/completions":
                    response_payload = normalize_chat_completion(
                        response_payload,
                        include_reasoning=include_reasoning,
                        prompt_template=prompt_template,
                    )
                    
                    # Apply anti-loop to JSON response
                    choices = response_payload.get("choices", [])
                    if choices:
                        content = choices[0].get("message", {}).get("content", "")
                        if content and detect_repetition(content, prompt_template=prompt_template):
                            choices[0]["message"]["content"] = truncate_at_repetition(
                                content, prompt_template=prompt_template
                            )
                            choices[0]["finish_reason"] = "length"
                    logger.info(
                        "data plane response normalized",
                        extra={
                            "extra_data": {
                                "endpoint": endpoint,
                                "backend_name": backend_name or backend,
                                "tool_calls": sanitize_tool_calls(
                                    [
                                        tool_call
                                        for choice in response_payload.get("choices", [])
                                        for tool_call in ((choice.get("message") or {}).get("tool_calls") or [])
                                        if isinstance(tool_call, dict)
                                    ]
                                ),
                            }
                        },
                    )
                # Real token counting: count completion tokens
                completion_text = ""
                if isinstance(response_payload, dict):
                    choices = response_payload.get("choices", [])
                    if choices and isinstance(choices[0], dict):
                        msg = choices[0].get("message")
                        if isinstance(msg, dict):
                            completion_text = msg.get("content") or ""
                        else:
                            completion_text = choices[0].get("text") or ""

                real_completion_tokens = 0
                try:
                    counting_res = token_counter.count_tokens("", completion_text, model_name, provider=backend)
                    real_completion_tokens = counting_res.completion_tokens
                    if counting_res.fallback_used:
                        fallback_used = True
                    if counting_res.tokenizer_used != "fallback":
                        tokenizer_used = counting_res.tokenizer_used
                except Exception as e:
                    logger.warning(f"Error counting completion tokens: {e}")

                if "usage" not in response_payload or not isinstance(response_payload["usage"], dict):
                    response_payload["usage"] = {}
                response_payload["usage"]["prompt_tokens"] = real_prompt_tokens
                response_payload["usage"]["completion_tokens"] = real_completion_tokens
                response_payload["usage"]["total_tokens"] = real_prompt_tokens + real_completion_tokens
                response_payload["usage"]["tokenizer_used"] = tokenizer_used
                response_payload["usage"]["fallback_used"] = fallback_used

                # Apply Model Provenance Watermarking (Advisory)
                try:
                    from app.services.model_provenance.service import StandardOutputWatermarker
                    watermarker = StandardOutputWatermarker()
                    run_id = response_payload.get("id", "unknown")
                    # We only watermark the content if it's chat completion for now
                    content_to_watermark = completion_text
                    if content_to_watermark:
                        wm_res = await watermarker.apply_watermark(content_to_watermark, model_name, run_id)
                        response_payload["watermark_info"] = wm_res
                        logger.info(f"Output watermarked: {wm_res['watermark_id']}")
                except Exception as wm_exc:
                    logger.warning(f"Watermarking failed: {wm_exc}")

                if endpoint == "/v1/chat/completions":
                    self._validate_chat_response_payload(
                        response_payload,
                        include_reasoning=include_reasoning,
                        backend_name=backend_name or backend,
                    )

                return ForwardResult(
                    response=JSONResponse(status_code=response.status_code, content=response_payload),
                    backend_name=backend_name,
                    attempts=1,
                    fallback_used=False,
                    backend_errors=[],
                    prompt_tokens=real_prompt_tokens,
                    completion_tokens=real_completion_tokens,
                    total_tokens=real_prompt_tokens + real_completion_tokens,
                    tokenizer_used=tokenizer_used,
                    real_fallback_used=fallback_used,
                )
            except (httpx.HTTPStatusError, httpx.TransportError) as exc:
                last_error = exc
                retriable = isinstance(exc, httpx.TransportError) or getattr(exc.response, "status_code", 500) >= 500
                if attempt > self.settings.retry_attempts or not retriable:
                    break
                await asyncio.sleep(self.settings.retry_backoff_seconds * attempt)
        if last_error is not None and self._should_trip_circuit_breaker(last_error):
            await self.circuit_breaker.record_failure()
        REQUEST_COUNTER.labels(endpoint=endpoint, status="error").inc()
        status_code = int(getattr(getattr(last_error, "response", None), "status_code", 503))
        elapsed = perf_counter() - started
        record_inference_latency(
            model=payload.get("model"),
            backend=backend_name or backend,
            plan=plan_code,
            endpoint=endpoint,
            status_code=status_code,
            latency_seconds=elapsed,
        )
        BACKEND_ERROR_COUNTER.labels(
            backend_name=backend_name or backend,
            endpoint=endpoint,
            status_code=str(status_code),
        ).inc()
        if status_code >= 500:
            record_backend_error(
                model=payload.get("model"),
                backend=backend_name or backend,
                plan=plan_code,
                endpoint=endpoint,
                status_code=status_code,
            )
        else:
            record_model_error(
                model=payload.get("model"),
                backend=backend_name or backend,
                plan=plan_code,
                endpoint=endpoint,
                status_code=status_code,
            )
        logger.warning("data plane request failed", extra={"extra_data": {"endpoint": endpoint, "error": str(last_error)}})
        if isinstance(last_error, httpx.HTTPStatusError) and last_error.response.status_code < 500:
            raise HTTPException(status_code=last_error.response.status_code, detail=self._backend_error_detail(last_error))
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="data plane unavailable")

    async def _streaming_forward(
        self,
        endpoint: str,
        payload: dict,
        include_reasoning: bool = False,
        backend: str = "llama.cpp",
        backend_url: str = "",
        backend_name: str = "",
        prompt_template: str | None = None,
        api_key: str | None = None,
        plan_code: str = "free",
    ) -> StreamingResponse:
        started = perf_counter()
        client = self._client_for_backend(backend, backend_url)
        
        # Ensure endpoint starts with /v1/ if it's chat/completions/embeddings and not already there
        target_endpoint = endpoint
        if not target_endpoint.startswith("/v1/") and any(t in target_endpoint for t in ["chat/completions", "completions", "embeddings"]):
            target_endpoint = f"/v1/{target_endpoint.lstrip('/')}"
        
        if backend == "openrouter" and target_endpoint.startswith("/v1/"):
            target_endpoint = self._normalize_openrouter_endpoint(backend_url, target_endpoint)
        request_payload = await self._prepare_chat_payload(
            payload,
            include_reasoning=include_reasoning,
            backend=backend,
            prompt_template=prompt_template,
        )
        if backend == "ollama":
            target_endpoint, request_payload = self._translate_ollama_request(endpoint, payload, stream=True)

        # Real token counting: count prompt tokens before call
        from app.services.token_counting.token_counter import TokenCounter
        token_counter = TokenCounter()

        model_name = request_payload.get("model") or payload.get("model") or ""
        messages = request_payload.get("messages") or request_payload.get("prompt") or payload.get("messages") or payload.get("prompt") or ""

        real_prompt_tokens = 0
        tokenizer_used = "fallback"
        fallback_used = True
        try:
            counting_res = token_counter.count_tokens(messages, "", model_name, provider=backend)
            real_prompt_tokens = counting_res.prompt_tokens
            tokenizer_used = counting_res.tokenizer_used
            fallback_used = counting_res.fallback_used
        except Exception as e:
            logger.warning(f"Error counting prompt tokens: {e}")

        
        # Secure debug log for payload
        logged_payload = self._sanitize_logged_payload(request_payload)
        logger.info(
            "forwarding stream request to data plane",
            extra={
                "extra_data": {
                    "endpoint": target_endpoint,
                    "payload": logged_payload,
                    "backend_url": backend_url,
                    "effective_params": {
                        "max_tokens": request_payload.get("max_tokens"),
                        "n_predict": request_payload.get("n_predict"),
                        "temperature": request_payload.get("temperature"),
                        "stop": request_payload.get("stop"),
                        "stream": request_payload.get("stream"),
                    }
                }
            },
        )
        
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        elif backend_name == "lmstudio-local" and self.settings.lmstudio_api_key:
            headers["Authorization"] = f"Bearer {self.settings.lmstudio_api_key}"

        stream_client = httpx.AsyncClient(base_url=backend_url, timeout=self.attempt_timeout)
        request = stream_client.build_request("POST", target_endpoint, json=request_payload, headers=headers)

        try:
            response = await stream_client.send(request, stream=True)
            response.raise_for_status()
            await self.circuit_breaker.record_success()
            BACKEND_LATENCY.labels(backend_name=backend_name or backend, endpoint=endpoint).observe(perf_counter() - started)
        except (httpx.HTTPStatusError, httpx.TransportError) as exc:
            await stream_client.aclose()
            if isinstance(exc, httpx.HTTPStatusError):
                try:
                    await exc.response.aread()
                except Exception:
                    pass
            if self._should_trip_circuit_breaker(exc):
                await self.circuit_breaker.record_failure()
            REQUEST_COUNTER.labels(endpoint=endpoint, status="error").inc()
            status_code = int(getattr(getattr(exc, "response", None), "status_code", 503))
            elapsed = perf_counter() - started
            record_inference_latency(
                model=payload.get("model"),
                backend=backend_name or backend,
                plan=plan_code,
                endpoint=endpoint,
                status_code=status_code,
                latency_seconds=elapsed,
            )
            BACKEND_ERROR_COUNTER.labels(
                backend_name=backend_name or backend,
                endpoint=endpoint,
                status_code=str(status_code),
            ).inc()
            if status_code >= 500:
                record_backend_error(
                    model=payload.get("model"),
                    backend=backend_name or backend,
                    plan=plan_code,
                    endpoint=endpoint,
                    status_code=status_code,
                )
            else:
                record_model_error(
                    model=payload.get("model"),
                    backend=backend_name or backend,
                    plan=plan_code,
                    endpoint=endpoint,
                    status_code=status_code,
                )
            logger.warning(
                "data plane stream setup failed",
                extra={"extra_data": {"endpoint": endpoint, "backend_name": backend_name, "error": str(exc)}},
            )
            if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code < 500:
                raise HTTPException(status_code=exc.response.status_code, detail=self._backend_error_detail(exc)) from exc
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="data plane unavailable") from exc

        async def event_stream():
            completion_fragments: list[str] = []
            loop_detected = False
            try:
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    if loop_detected:
                        # We already detected a loop, stop yielding real content
                        # We might yield [DONE] if we want to finish gracefully
                        break
                    if backend == "ollama":
                        translated_line = self._translate_ollama_stream_line(line, endpoint, payload.get("model", ""))
                        if translated_line is None:
                            continue
                        line = translated_line
                    if line.startswith("data: ") and line != "data: [DONE]":
                        try:
                            parsed = json.loads(line.removeprefix("data: "))
                            delta_obj = parsed.get("choices", [{}])[0].get("delta", {})
                            delta_content = delta_obj.get("content") or ""
                            delta_reasoning = delta_obj.get("reasoning_content") or delta_obj.get("reasoning") or ""
                            delta_text = parsed.get("choices", [{}])[0].get("text") or ""
                            delta = f"{delta_reasoning}{delta_content}{delta_text}"
                            completion_fragments.append(delta)
                            
                            # Anti-loop check on accumulated content
                            accumulated = "".join(completion_fragments)
                            if len(completion_fragments) % 5 == 0 and detect_repetition(accumulated, prompt_template=prompt_template):
                                loop_detected = True
                                # Yield a final chunk with truncation notice
                                truncation_chunk = {
                                    "choices": [{
                                        "index": 0,
                                        "delta": {"content": "\n\n[Truncated due to repetition loop]"},
                                        "finish_reason": "length"
                                    }]
                                }
                                yield f"data: {json.dumps(truncation_chunk)}\n\n"
                                yield "data: [DONE]\n\n"
                                break

                        except json.JSONDecodeError:
                            pass
                    if endpoint == "/v1/chat/completions":
                        normalized_line = normalize_chat_stream_line(
                            line,
                            include_reasoning=include_reasoning,
                            prompt_template=prompt_template,
                        )
                        if normalized_line is None:
                            continue
                        yield f"{normalized_line}\n\n"
                        continue
                    yield f"{line}\n\n"
            except (httpx.HTTPStatusError, httpx.TransportError) as exc:
                if self._should_trip_circuit_breaker(exc):
                    await self.circuit_breaker.record_failure()
                error_event = {"error": {"message": "stream interrupted", "type": exc.__class__.__name__}}
                yield f"data: {json.dumps(error_event)}\n\n"
            finally:
                await response.aclose()
                await stream_client.aclose()
                REQUEST_COUNTER.labels(endpoint=endpoint, status="success").inc()
                elapsed = perf_counter() - started
                REQUEST_LATENCY.labels(endpoint=endpoint).observe(elapsed)
                record_inference_latency(
                    model=payload.get("model"),
                    backend=backend_name or backend,
                    plan=plan_code,
                    endpoint=endpoint,
                    status_code=200,
                    latency_seconds=elapsed,
                )
                
                # Real token counting: count completion tokens
                completion_text = "".join(completion_fragments)
                real_completion_tokens = 0
                try:
                    counting_res = token_counter.count_tokens("", completion_text, model_name, provider=backend)
                    real_completion_tokens = counting_res.completion_tokens
                    if counting_res.fallback_used:
                        fallback_used = True
                    if counting_res.tokenizer_used != "fallback":
                        tokenizer_used = counting_res.tokenizer_used
                except Exception as e:
                    logger.warning(f"Error counting completion tokens: {e}")

                logger.info(
                    "stream completed",
                    extra={"extra_data": {
                        "endpoint": endpoint,
                        "completion_tokens_estimated": real_completion_tokens,
                        "tokenizer_used": tokenizer_used,
                        "fallback_used": fallback_used
                    }},
                )

                # Update the database log and financials with actual values
                from app.core.metrics import get_correlation_id
                corr_id = get_correlation_id()
                if corr_id:
                    try:
                        from app.db.session import SessionLocal
                        from app.models.billing.request_financial import RequestFinancial
                        from app.models.core.request_log import RequestLog
                        from app.services.quota import update_usage_with_real_tokens
                        from sqlalchemy import select

                        async with SessionLocal() as db_session:
                            stmt_log = select(RequestLog).where(RequestLog.correlation_id == corr_id)
                            res_log = await db_session.execute(stmt_log)
                            req_log = res_log.scalar_one_or_none()

                            if req_log:
                                est_prompt = req_log.prompt_tokens_estimated or 0
                                est_completion = req_log.completion_tokens_estimated or 0
                                
                                req_log.prompt_tokens_estimated = real_prompt_tokens
                                req_log.completion_tokens_estimated = real_completion_tokens
                                
                                await update_usage_with_real_tokens(
                                    db_session,
                                    client_id=req_log.client_id,
                                    estimated_prompt=est_prompt,
                                    estimated_completion=est_completion,
                                    real_prompt=real_prompt_tokens,
                                    real_completion=real_completion_tokens,
                                    token_count_method=tokenizer_used,
                                )

                                stmt_fin = select(RequestFinancial).where(RequestFinancial.request_log_id == req_log.id)
                                res_fin = await db_session.execute(stmt_fin)
                                req_fin = res_fin.scalar_one_or_none()
                                if req_fin:
                                    req_fin.prompt_tokens = real_prompt_tokens
                                    req_fin.completion_tokens = real_completion_tokens
                                    req_fin.total_tokens = real_prompt_tokens + real_completion_tokens
                                    req_fin.token_count_method = tokenizer_used
                                    req_fin.tokens_estimated = fallback_used
                                    
                                await db_session.commit()
                    except Exception as db_exc:
                        logger.warning(f"Error updating stream real tokens in DB: {db_exc}")

        return ForwardResult(
            response=StreamingResponse(event_stream(), media_type="text/event-stream"),
            backend_name=backend_name,
            attempts=1,
            fallback_used=False,
            backend_errors=[],
            prompt_tokens=real_prompt_tokens,
            completion_tokens=0,
            total_tokens=real_prompt_tokens,
            tokenizer_used=tokenizer_used,
            real_fallback_used=fallback_used,
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
