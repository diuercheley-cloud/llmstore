import abc
import difflib
import asyncio
import contextlib
import json
import logging
import os
from collections.abc import AsyncIterator
from typing import Any

import httpx

from .sanitizer import Sanitizer
from .schemas import AgentActionResponse

logger = logging.getLogger(__name__)


class CodeAgentProvider(abc.ABC):
    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.agent_id = config.get("agent_id", "default")
        self.model = config.get("model", "")
        self.base_url = (config.get("base_url") or "").rstrip("/")
        self.api_key_env = config.get("api_key_env", "OPENAI_API_KEY")
        self.timeout = float(config.get("timeout", 30.0))
        self.max_retries = max(0, int(config.get("max_retries", 3)))
        self.stream = bool(config.get("stream", False))
        self.transport = config.get("transport")

        # Instantiate the real CodeAgent class to represent/validate this provider's agent helper
        provider_name = config.get("provider")
        if not provider_name:
            cls_name = self.__class__.__name__.lower()
            if "local" in cls_name:
                provider_name = "local-openai-compatible"
            elif "openai" in cls_name:
                provider_name = "openai-compatible"
            elif "control" in cls_name:
                provider_name = "control-plane"
            elif "anthropic" in cls_name:
                provider_name = "anthropic"
            elif "google" in cls_name:
                provider_name = "google"
            else:
                provider_name = "stub"

        from ._code_agents import CodeAgent
        self.agent_helper = CodeAgent(
            agent_id=self.agent_id,
            provider=provider_name,
            config=config
        )


    UNSUPPORTED_MEDIA_TYPES = frozenset({"audio_url", "video_url"})

    def _warn_unsupported_media(self, content: Any) -> list[dict[str, Any]]:
        if not isinstance(content, list):
            return [{"type": "text", "text": str(content)}]
        filtered = []
        for block in content:
            if block.get("type") in self.UNSUPPORTED_MEDIA_TYPES:
                mtype = block.get("type", "media")
                meta = block.get("metadata", {})
                mime = meta.get("mime_type", "unknown")
                logger.warning(
                    "Provider %s does not support %s (mime=%s).",
                    self.__class__.__name__, mtype, mime,
                )
                text = f"[{mtype} skipped — {mime} not supported by this provider]"
                filtered.append({
                    "type": "text",
                    "text": text,
                })
            else:
                filtered.append(block)
        return filtered

    @abc.abstractmethod
    async def chat_completion(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        pass

    @abc.abstractmethod
    async def health_check(self) -> dict[str, Any]:
        pass

    def _get_api_key(self) -> str:
        return os.getenv(self.api_key_env, "")

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"agent_id={self.agent_id!r}, "
            f"base_url={self.base_url!r}, "
            f"model={self.model!r}, "
            f"api_key_env={self.api_key_env!r}, "
            f"timeout={self.timeout!r}, "
            f"max_retries={self.max_retries!r})"
        )

    def _normalize_action_payload(self, action: dict[str, Any]) -> dict[str, Any]:
        valid_types = {
            "plan",
            "read_file",
            "apply_patch",
            "run_shell",
            "run_tests",
            "final",
        }
        action_type = action.get("type")
        if action_type not in valid_types:
            raise ValueError(f"Invalid action type: {action_type}")

        payload = action.get("payload", {})
        if not isinstance(payload, dict):
            raise ValueError("Action payload must be a JSON object")

        normalized = {"action_type": action_type}
        if action.get("reason"):
            normalized["reason"] = str(action["reason"])
        normalized.update(payload)
        return normalized

    def _validate_and_transform_action(self, content: str) -> str:
        cleaned = content.strip()
        if cleaned.startswith("```") and cleaned.endswith("```"):
            cleaned = cleaned[3:-3].strip()
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()

        try:
            action_data = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.error("Invalid JSON action from agent: %s", Sanitizer.sanitize_text(cleaned))
            raise ValueError("invalid_json")

        if not isinstance(action_data, dict):
            raise ValueError("invalid_payload")

        action_type = action_data.get("type")
        if not action_type:
            raise ValueError("schema_validation_failed")

        supported = {
            "plan", "read_file", "apply_patch", "run_shell",
            "run_tests", "parallel", "final", "grep",
            "ast_search", "list_files", "replace_content"
        }
        if action_type not in supported:
            raise ValueError("unsupported_action")

        try:
            from pydantic import ValidationError
            validated = AgentActionResponse.model_validate(action_data).root
            action_dict = validated.model_dump()
            normalized = self._normalize_action_payload(action_dict)
            return json.dumps(normalized)
        except ValidationError as exc:
            logger.error("Schema validation failed for agent action: %s", exc)
            raise ValueError("schema_validation_failed") from exc
        except Exception as exc:
            logger.error("Unexpected error during action validation: %s", exc)
            raise ValueError(f"schema_validation_failed: {exc}") from exc

    def _sanitize_response(self, response_data: dict[str, Any]) -> dict[str, Any]:
        return Sanitizer.sanitize_data(response_data)

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs,
    ) -> httpx.Response:
        headers = kwargs.get("headers", {})
        log_headers = Sanitizer.sanitize_data(headers)
        log_payload = None
        if "json" in kwargs:
            log_payload = Sanitizer.sanitize_data(kwargs["json"])

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            transport=self.transport,
        ) as client:
            for attempt in range(self.max_retries + 1):
                try:
                    logger.debug(
                        "Request %s %s attempt=%s headers=%s payload=%s",
                        method,
                        url,
                        attempt + 1,
                        log_headers,
                        log_payload,
                    )
                    response = await client.request(method, url, **kwargs)

                    if response.status_code in [502, 503, 504]:
                        if attempt < self.max_retries:
                            wait = 2**attempt
                            await asyncio.sleep(wait)
                            continue

                    response.raise_for_status()
                    return response
                except (httpx.TimeoutException, httpx.NetworkError):
                    if attempt < self.max_retries:
                        wait = 2**attempt
                        await asyncio.sleep(wait)
                        continue
                    raise
                except httpx.HTTPStatusError as e:
                    if 400 <= e.response.status_code < 500:
                        raise
                    if attempt < self.max_retries:
                        wait = 2**attempt
                        await asyncio.sleep(wait)
                        continue
                    raise
        raise RuntimeError("Request failed after retries")


class StubProvider(CodeAgentProvider):
    async def chat_completion(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        for m in messages:
            if isinstance(m.get("content"), list) and not self.config.get("multimodal", False):
                raise ValueError(
                    "Provider or model does not support multimodal input. "
                    "Enable 'multimodal' or choose a multimodal model."
                )
        logger.warning(
            "StubProvider in use: no real LLM execution will be performed. "
            "This is intended for infrastructure testing only. "
            "Pass --allow-stub-code-agent to acknowledge."
        )
        return {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": json.dumps(
                            {
                                "action_type": "final",
                                "message": "Task completed (simulated by StubProvider)",
                            }
                        ),
                    }
                }
            ],
            "usage": {"total_tokens": 150},
        }

    async def health_check(self) -> dict[str, Any]:
        logger.warning(
            "StubProvider health check: no real provider is connected. "
            "Use --allow-stub-code-agent for testing only."
        )
        return {
            "status": "healthy",
            "provider": "stub",
            "message": "stub provider enabled (no real LLM)",
        }


class OpenAICompatibleProvider(CodeAgentProvider):
    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self._supports_response_format = True
        self._available_models: list[str] | None = None

    def _validate_config(self):
        self.agent_helper.validate_config()
        if not self._get_api_key():
            raise ValueError(
                f"API key not found in environment variable {self.api_key_env} "
                f"for provider {self.config.get('provider')}"
            )


    def _build_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        api_key = self._get_api_key()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    def _build_chat_paths(self) -> list[str]:
        base = self.base_url
        direct_paths: list[str] = []
        if base.endswith("/v1"):
            direct_paths.extend(["/chat/completions", "/responses"])
        elif base.endswith("/chat/completions") or base.endswith("/responses"):
            return [base]
        else:
            direct_paths.extend(["/v1/chat/completions", "/v1/responses"])

        urls = []
        for path in direct_paths:
            if path.startswith("http://") or path.startswith("https://"):
                urls.append(path)
            else:
                base_u = self.base_url
                if base_u.endswith("/v1") and path.startswith("/v1/"):
                    path = path[3:]
                urls.append(f"{base_u}{path}")
        return urls

    def _build_models_url(self) -> str:
        base = self.base_url
        if base.endswith("/v1/models"):
            return base
        if base.endswith("/v1"):
            return f"{base}/models"
        return f"{base}/v1/models"

    @staticmethod
    def _parse_model_catalog(data: Any) -> list[str]:
        items = data.get("data") if isinstance(data, dict) else data
        if not isinstance(items, list):
            return []
        model_ids: list[str] = []
        for item in items:
            if isinstance(item, dict):
                model_id = item.get("id")
                if isinstance(model_id, str) and model_id:
                    model_ids.append(model_id)
        return model_ids

    async def _fetch_available_models(self, refresh: bool = False) -> list[str]:
        if self._available_models is not None and not refresh:
            return self._available_models

        response = await self._request_with_retry(
            "GET", self._build_models_url(), headers=self._build_headers()
        )
        models = self._parse_model_catalog(response.json())
        self._available_models = models
        return models

    def _match_model_in_catalog(self, available_models: list[str]) -> str | None:
        if self.model and self.model in available_models:
            return self.model
        if not self.model and available_models:
            return available_models[0]
        return None

    async def _resolve_local_model(self, *, allow_auto_select: bool) -> str:
        available_models = await self._fetch_available_models()
        if not available_models:
            raise ValueError(
                f"No models returned by {self._build_models_url()} for provider {self.config.get('provider')}"
            )

        selected = self._match_model_in_catalog(available_models)
        if selected is None:
            close_matches: list[str] = []
            if self.model:
                close_matches = difflib.get_close_matches(
                    self.model,
                    available_models,
                    n=3,
                    cutoff=0.45,
                )
            preview = ", ".join(available_models[:5])
            if len(available_models) > 5:
                preview += ", ..."
            suggestion_text = ""
            if close_matches:
                suggestion_text = f" Suggested models: {', '.join(close_matches)}."
            raise ValueError(
                f"Requested model '{self.model}' was not found at {self._build_models_url()}. "
                f"Available models: {preview}.{suggestion_text}"
            )

        if allow_auto_select and not self.model:
            self.model = selected

        return selected

    async def chat_completion(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        self._validate_config()
        instruction = (
            "Return exactly one JSON object with this schema: "
            '{"type":"plan|read_file|apply_patch|run_shell|run_tests|final",'
            '"reason":"short explanation","payload":{}}. '
            "Do not wrap JSON in markdown."
        )
        enriched_messages = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if isinstance(content, list):
                if not self.config.get("multimodal", False):
                    raise ValueError(
                        "Provider or model does not support multimodal input. "
                        "Enable 'multimodal' or choose a multimodal model."
                    )
                sanitized_content = []
                for block in content:
                    if block.get("type") == "text":
                        sanitized_content.append({
                            "type": "text",
                            "text": Sanitizer.strip_control_chars(block.get("text", ""))
                        })
                    else:
                        sanitized_content.append(block)
                enriched_messages.append({"role": role, "content": sanitized_content})
            else:
                enriched_messages.append({
                    "role": role,
                    "content": Sanitizer.strip_control_chars(str(content))
                })
        enriched_messages.append({"role": "system", "content": instruction})

        last_error: Exception | None = None
        for url in self._build_chat_paths():
            try:
                payload = {
                    "model": self.model,
                    "messages": enriched_messages,
                    "temperature": 0,
                    "stream": self.stream,
                }
                if not self.stream and self._supports_response_format:
                    payload["response_format"] = {"type": "json_object"}

                if self.stream:
                    return await self._chat_completion_stream(url, payload)

                response = await self._request_with_retry(
                    "POST", url, json=payload, headers=self._build_headers()
                )
                data = response.json()
                return self._process_chat_response(data)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    last_error = exc
                    continue
                if exc.response.status_code == 400 and self._supports_response_format:
                    self._supports_response_format = False
                    logger.debug(
                        "Provider rejected response_format=json_object; "
                        "retrying without response_format for subsequent calls"
                    )
                    try:
                        payload = {
                            "model": self.model,
                            "messages": enriched_messages,
                            "temperature": 0,
                        }
                        response = await self._request_with_retry(
                            "POST", url, json=payload, headers=self._build_headers()
                        )
                        data = response.json()
                        return self._process_chat_response(data)
                    except Exception as fallback_exc:
                        last_error = fallback_exc
                        raise
                raise
            except ValueError as exc:
                last_error = exc
                raise
        raise ValueError(
            "OpenAI-compatible provider did not expose a supported endpoint"
        ) from last_error

    async def _chat_completion_stream(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        full_content = ""
        usage = {"total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0}

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout), transport=self.transport
        ) as client:
            headers = self._build_headers()
            async with client.stream("POST", url, json=payload, headers=headers) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue

                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break

                    try:
                        chunk = json.loads(data_str)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        if "content" in delta:
                            content_delta = delta["content"]
                            full_content += content_delta
                            # We could emit an event here if we had a callback

                        if chunk.get("usage"):
                            usage = chunk["usage"]
                    except json.JSONDecodeError:
                        continue

        # Mocking the response structure that _process_chat_response expects
        data = {
            "choices": [{"message": {"role": "assistant", "content": full_content}}],
            "usage": usage
        }
        return self._process_chat_response(data)

    def _process_chat_response(self, data: dict[str, Any]) -> dict[str, Any]:
        content = ""
        if isinstance(data.get("choices"), list) and len(data["choices"]) > 0:
            content = str(data["choices"][0].get("message", {}).get("content", ""))

        if not content:
            raise ValueError("Provider returned empty content")

        validated_content = self._validate_and_transform_action(content)
        data.setdefault("choices", [{"message": {"role": "assistant", "content": ""}}])
        data["choices"][0]["message"]["content"] = validated_content
        usage = data.get("usage", {})
        if not usage:
            data["usage"] = {"total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0}
        return self._sanitize_response(data)

    async def health_check(self) -> dict[str, Any]:
        self._validate_config()
        models = await self._fetch_available_models(refresh=True)
        details: dict[str, Any] = {
            "models_url": self._build_models_url(),
            "available_models": models,
            "supports_response_format": self._supports_response_format,
        }
        if not models:
            details["status_detail"] = "no_models_listed"
            return {
                "status": "unhealthy",
                "provider": "openai-compatible",
                "error": f"No models were listed by {self._build_models_url()}.",
                "details": details,
            }
        if self.model:
            if self.model not in models:
                close_matches = difflib.get_close_matches(self.model, models, n=3, cutoff=0.45)
                details["selected_model"] = self.model
                details["status_detail"] = "model_not_listed"
                details["suggested_models"] = close_matches
                return {
                    "status": "unhealthy",
                    "provider": "openai-compatible",
                    "error": (
                        f"Model '{self.model}' was not listed by {self._build_models_url()}."
                    ),
                    "details": details,
                }
            details["selected_model"] = self.model
        else:
            details["selected_model"] = models[0] if models else None
        return {"status": "healthy", "provider": "openai-compatible", "details": details}


class LocalOpenAICompatibleProvider(OpenAICompatibleProvider):
    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self._supports_response_format = False

    def _validate_config(self):
        # Override to bypass API key requirement for local development models (Ollama, LM Studio)
        self.agent_helper.validate_config()


    def _build_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        api_key = self._get_api_key()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    async def chat_completion(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        self._validate_config()
        await self._resolve_local_model(allow_auto_select=True)
        return await super().chat_completion(messages)

    async def health_check(self) -> dict[str, Any]:
        self._validate_config()
        selected_model = await self._resolve_local_model(allow_auto_select=True)
        return {
            "status": "healthy",
            "provider": "local-openai-compatible",
            "details": {
                "models_url": self._build_models_url(),
                "available_models": self._available_models or [],
                "selected_model": selected_model,
                "supports_response_format": self._supports_response_format,
                "auto_selected_model": not bool(self.config.get("model")),
            },
        }


class AnthropicProvider(CodeAgentProvider):
    def _validate_config(self):
        if not self._get_api_key():
            raise ValueError(
                f"API key not found in environment variable {self.api_key_env} "
                "for provider anthropic"
            )

    def _build_headers(self) -> dict[str, str]:
        headers = {
            "content-type": "application/json",
            "x-api-key": self._get_api_key(),
            "anthropic-version": "2023-06-01",
        }
        return headers

    def _convert_to_anthropic_content(self, content: Any) -> list[dict[str, Any]]:
        content = self._warn_unsupported_media(content)
        if isinstance(content, list):
            anthropic_blocks = []
            for block in content:
                if block.get("type") == "text":
                    anthropic_blocks.append({
                        "type": "text",
                        "text": block.get("text", ""),
                    })
                elif block.get("type") == "image_url":
                    img_url = block.get("image_url", {}).get("url", "")
                    if img_url.startswith("data:"):
                        mime_part, _, b64_data = img_url[5:].partition(";base64,")
                        anthropic_blocks.append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mime_part or "image/png",
                                "data": b64_data,
                            },
                        })
                    else:
                        anthropic_blocks.append(block)
                else:
                    anthropic_blocks.append(block)
            return anthropic_blocks
        return [{"type": "text", "text": str(content)}]

    async def chat_completion(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        self._validate_config()
        url = f"{self.base_url}/v1/messages" if self.base_url else "https://api.anthropic.com/v1/messages"

        system_content = []
        anthropic_messages = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "system":
                system_content.append(content)
            else:
                if role not in ["user", "assistant"]:
                    role = "user"
                anthropic_messages.append({
                    "role": role,
                    "content": self._convert_to_anthropic_content(content),
                })

        instruction = (
            "Return exactly one JSON object with this schema: "
            '{"type":"plan|read_file|apply_patch|run_shell|run_tests|final",'
            '"reason":"short explanation","payload":{}}. "Do not wrap JSON in markdown.'
        )
        system_content.append(instruction)

        payload = {
            "model": self.model or "claude-3-5-sonnet-20241022",
            "messages": anthropic_messages,
            "system": "\n".join(system_content),
            "max_tokens": 4096,
        }

        response = await self._request_with_retry(
            "POST", url, json=payload, headers=self._build_headers()
        )
        data = response.json()

        content = ""
        if isinstance(data.get("content"), list) and len(data["content"]) > 0:
            content = data["content"][0].get("text", "")

        if not content:
            raise ValueError("Anthropic provider returned empty content")

        validated_content = self._validate_and_transform_action(content)

        standardized = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": validated_content,
                    }
                }
            ],
            "usage": {
                "prompt_tokens": data.get("usage", {}).get("input_tokens", 0),
                "completion_tokens": data.get("usage", {}).get("output_tokens", 0),
                "total_tokens": data.get("usage", {}).get("input_tokens", 0)
                + data.get("usage", {}).get("output_tokens", 0)
            },
        }
        return self._sanitize_response(standardized)

    async def health_check(self) -> dict[str, Any]:
        self._validate_config()
        return {"status": "healthy", "provider": "anthropic"}


class GoogleProvider(CodeAgentProvider):
    def _validate_config(self):
        if not self._get_api_key():
            raise ValueError(
                f"API key not found in environment variable {self.api_key_env} "
                "for provider google"
            )

    def _convert_to_google_parts(self, content: Any) -> list[dict[str, Any]]:
        content = self._warn_unsupported_media(content)
        if isinstance(content, list):
            parts = []
            for block in content:
                if block.get("type") == "text":
                    parts.append({"text": block.get("text", "")})
                elif block.get("type") == "image_url":
                    img_url = block.get("image_url", {}).get("url", "")
                    if img_url.startswith("data:"):
                        mime_part, _, b64_data = img_url[5:].partition(";base64,")
                        parts.append({
                            "inline_data": {
                                "mime_type": mime_part or "image/png",
                                "data": b64_data,
                            },
                        })
                    else:
                        parts.append({"text": str(block)})
                else:
                    parts.append({"text": str(block)})
            return parts
        return [{"text": str(content)}]

    async def chat_completion(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        self._validate_config()
        api_key = self._get_api_key()
        model = self.model or "gemini-1.5-pro"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        if self.base_url:
            url = f"{self.base_url}/v1beta/models/{model}:generateContent"

        system_content = []
        contents = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "system":
                system_content.append(content)
            else:
                mapped_role = "user" if role == "user" else "model"
                contents.append({
                    "role": mapped_role,
                    "parts": self._convert_to_google_parts(content),
                })

        instruction = (
            "Return exactly one JSON object with this schema: "
            '{"type":"plan|read_file|apply_patch|run_shell|run_tests|final",'
            '"reason":"short explanation","payload":{}}. '
            "Do not wrap JSON in markdown."
        )
        system_content.append(instruction)

        payload = {
            "contents": contents,
            "systemInstruction": {
                "parts": [{"text": "\n".join(system_content)}]
            },
            "generationConfig": {
                "responseMimeType": "application/json"
            },
        }

        response = await self._request_with_retry(
            "POST",
            url,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": api_key,
            },
        )

        data = response.json()

        content = ""
        with contextlib.suppress(KeyError, IndexError):
            content = data["candidates"][0]["content"]["parts"][0]["text"]

        if not content:
            raise ValueError("Google Gemini provider returned empty content")

        validated_content = self._validate_and_transform_action(content)

        standardized = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": validated_content,
                    }
                }
            ],
            "usage": {
                "prompt_tokens": data.get("usageMetadata", {}).get("promptTokenCount", 0),
                "completion_tokens": data.get("usageMetadata", {}).get("candidatesTokenCount", 0),
                "total_tokens": data.get("usageMetadata", {}).get("totalTokenCount", 0)
            },
        }
        return self._sanitize_response(standardized)

    async def health_check(self) -> dict[str, Any]:
        self._validate_config()
        return {"status": "healthy", "provider": "google"}


class ControlPlaneProvider(CodeAgentProvider):
    def _validate_config(self):
        self.agent_helper.validate_config()


    def _build_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        api_key = self._get_api_key()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    async def chat_completion(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        self._validate_config()
        try:
            await self.list_agents()
        except httpx.ConnectError:
            raise RuntimeError(
                f"Cannot connect to control plane at {self.base_url}. "
                "Ensure the LLM Inference Stack agentic runtime is running and reachable."
            )
        except httpx.TimeoutException:
            raise RuntimeError(
                f"Control plane at {self.base_url} timed out. "
                "Check if the service is healthy."
            )
        task = str(messages[-1]["content"]) if messages else ""
        run_data = await self.start_run(task)
        run_id = run_data.get("id")
        if not run_id:
            raise ValueError("Control plane response did not contain a run ID")

        pending_action: dict[str, Any] | None = None
        events_url = f"{self.base_url}/v1/agents/runs/{run_id}/events"
        async for event in self._stream_sse_events(events_url):
            action = self._convert_control_plane_event_to_action(event)
            if action is not None:
                pending_action = action
            event_type = event.get("type") or event.get("event")
            if event_type == "run.failed":
                message = event.get("message") or event.get("error") or "Control plane run failed"
                raise RuntimeError(str(message))
            if event_type == "run.completed":
                completion_action = self._action_from_run_completion(event)
                if completion_action is not None:
                    return self._wrap_action(completion_action)
                if pending_action is not None:
                    return self._wrap_action(pending_action)
                message = event.get("message") or "Run completed"
                return self._wrap_action(
                    self._normalize_action_payload(
                        {
                            "type": "final",
                            "reason": "run.completed",
                            "payload": {"message": str(message)},
                        }
                    )
                )

        if pending_action is not None:
            return self._wrap_action(pending_action)
        raise RuntimeError("Control plane run finished without actionable events")

    async def start_run(self, task: str) -> dict[str, Any]:
        self._validate_config()
        start_url = f"{self.base_url}/v1/agents/{self.agent_id}/runs"
        payload = {"input_text": task}
        try:
            response = await self._request_with_retry(
                "POST", start_url, json=payload, headers=self._build_headers()
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ValueError(f"Agent {self.agent_id} not found in control plane")
            raise
        return response.json()

    async def list_agents(self) -> list[dict[str, Any]]:
        self._validate_config()
        response = await self._request_with_retry(
            "GET", f"{self.base_url}/v1/agents", headers=self._build_headers()
        )
        data = response.json()
        if not isinstance(data, list):
            raise ValueError("Control plane agent list response must be a list")
        return data

    async def get_agent_config(self) -> dict[str, Any]:
        self._validate_config()
        response = await self._request_with_retry(
            "GET", f"{self.base_url}/v1/agents/{self.agent_id}", headers=self._build_headers()
        )
        return response.json()

    async def health_check(self) -> dict[str, Any]:
        self._validate_config()
        try:
            await self._request_with_retry(
                "GET",
                f"{self.base_url}/health",
                headers=self._build_headers(),
            )
        except httpx.ConnectError:
            return {
                "status": "unhealthy",
                "provider": "control-plane",
                "error": f"Cannot connect to control plane at {self.base_url}. "
                "Ensure the agentic runtime is running.",
            }
        try:
            agents = await self.list_agents()
        except httpx.ConnectError:
            return {
                "status": "unhealthy",
                "provider": "control-plane",
                "error": f"Control plane at {self.base_url} is reachable but agent list failed.",
            }
        return {
            "status": "healthy",
            "provider": "control-plane",
            "agents_count": len(agents),
        }

    async def _stream_sse_events(self, url: str) -> AsyncIterator[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=None, transport=self.transport) as client:
            async with client.stream("GET", url, headers=self._build_headers()) as response:
                response.raise_for_status()
                event_name: str | None = None
                async for raw_line in response.aiter_lines():
                    line = raw_line.strip()
                    if not line:
                        event_name = None
                        continue
                    if line.startswith("event:"):
                        event_name = line.split(":", 1)[1].strip()
                        continue
                    if not line.startswith("data:"):
                        continue
                    raw_data = line.split(":", 1)[1].strip()
                    if not raw_data:
                        continue
                    try:
                        payload = json.loads(raw_data)
                    except json.JSONDecodeError:
                        logger.debug(
                            "Ignoring non-JSON SSE payload: %s",
                            raw_data,
                        )
                        continue
                    if isinstance(payload, dict) and event_name:
                        payload.setdefault("event", event_name)
                    yield payload

    def _action_from_run_completion(self, event: dict[str, Any]) -> dict[str, Any] | None:
        output = event.get("output")
        if isinstance(output, dict):
            if "action_type" in output:
                return output
            valid_types = {"plan", "read_file", "apply_patch", "run_shell", "run_tests", "final"}
            if output.get("type") in valid_types:
                return self._normalize_action_payload(
                    {
                        "type": output["type"],
                        "reason": output.get("reason", "run.completed"),
                        "payload": output.get("payload", output),
                    }
                )
        return None

    def _convert_control_plane_event_to_action(
        self, event: dict[str, Any]
    ) -> dict[str, Any] | None:
        action_types = {"plan", "read_file", "apply_patch", "run_shell", "run_tests", "final"}
        event_type = event.get("type") or event.get("event")
        if event_type in action_types:
            payload = event.get("payload", event)
            if not isinstance(payload, dict):
                payload = {}
            action = {
                "type": event_type,
                "reason": event.get("reason", event_type),
                "payload": payload,
            }
            return self._normalize_action_payload(action)

        tool_name = event.get("tool_name")
        if event_type == "tool.called" and tool_name in action_types:
            payload = dict(event.get("parameters") or {})
            action = {
                "type": tool_name,
                "reason": event.get("reason", tool_name),
                "payload": payload,
            }
            return self._normalize_action_payload(action)

        return None

    def _wrap_action(self, action: dict[str, Any]) -> dict[str, Any]:
        return {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": json.dumps(self._sanitize_response(action)),
                    }
                }
            ]
        }


_PROVIDER_REGISTRY: dict[str, type[CodeAgentProvider]] = {}


def register_provider(name: str, provider_cls: type[CodeAgentProvider]):
    _PROVIDER_REGISTRY[name] = provider_cls


def create_code_agent(provider_name: str, config: dict[str, Any]) -> CodeAgentProvider:
    if provider_name not in _PROVIDER_REGISTRY:
        raise ValueError(f"Unknown provider: {provider_name}")
    cfg = dict(config)
    if "provider" not in cfg:
        cfg["provider"] = provider_name
    return _PROVIDER_REGISTRY[provider_name](cfg)


register_provider("stub", StubProvider)
register_provider("openai-compatible", OpenAICompatibleProvider)
register_provider("local-openai-compatible", LocalOpenAICompatibleProvider)
register_provider("anthropic", AnthropicProvider)
register_provider("google", GoogleProvider)
register_provider("control-plane", ControlPlaneProvider)
