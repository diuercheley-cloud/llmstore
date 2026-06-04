import abc
import asyncio
import contextlib
import difflib
import json
import logging
import os
import re
import time
from collections.abc import AsyncIterator
from typing import Any
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel

from .sanitizer import Sanitizer
from .schemas import (
    AgentActionResponse,
    ApplyPatchPayload,
    AstSearchPayload,
    FinalPayload,
    GrepPayload,
    ListFilesPayload,
    PlanPayload,
    ReadFilePayload,
    ReplaceContentPayload,
    RunShellPayload,
    RunTestsPayload,
    WriteFilePayload,
)

logger = logging.getLogger(__name__)

_PROBE_CACHE: dict[str, dict[str, Any]] = {}
_RESPONSE_FORMAT_CACHE: dict[str, bool] = {}


def _reasoning_indicates_probe_tool_call(reasoning_content: Any) -> bool:
    if not isinstance(reasoning_content, str):
        return False
    normalized = reasoning_content.lower()
    return "<function=probe>" in normalized or '"name":"probe"' in normalized


def _extract_textual_tool_call(reasoning_content: Any) -> dict[str, Any] | None:
    if not isinstance(reasoning_content, str) or "<tool_call>" not in reasoning_content:
        return None
    function_match = re.search(r"<function=([a-zA-Z0-9_\-]+)>", reasoning_content)
    if not function_match:
        return None
    function_name = function_match.group(1).strip()
    parameters: dict[str, str] = {}
    for match in re.finditer(
        r"<parameter=([a-zA-Z0-9_\-]+)>\s*(.*?)\s*</parameter>",
        reasoning_content,
        re.DOTALL,
    ):
        parameters[match.group(1).strip()] = match.group(2).strip()
    return {
        "id": f"lmstudio_{function_name}",
        "type": "function",
        "function": {
            "name": function_name,
            "arguments": json.dumps(parameters, ensure_ascii=True),
        },
    }


class CodeAgentProvider(abc.ABC):
    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.agent_id = config.get("agent_id", "default")
        self.model = config.get("model", "")
        self.base_url = (config.get("base_url") or "").rstrip("/")
        self.api_key_env = config.get("api_key_env", "OPENAI_API_KEY")
        self.timeout = float(config.get("timeout", 30.0))
        self.local_model_timeout = float(config.get("local_model_timeout", 300.0))
        self.auto_increase_timeout = bool(config.get("auto_increase_timeout", False))
        self.max_retries = max(0, int(config.get("max_retries", 3)))
        self.stream_local_default = bool(config.get("stream_local_default", True))
        self.verbose_stream = bool(config.get("verbose_stream", False))
        self.tool_calling = str(config.get("tool_calling", "auto"))
        self.event_callback = config.get("event_callback")
        self.transport = config.get("transport")
        self.supports_tool_calling = bool(config.get("supports_tool_calling", False))
        self.allow_native_tools_for_local = bool(config.get("allow_native_tools_for_local", False))
        self.lm_studio_compatibility = bool(config.get("lm_studio_compatibility", True))
        self.capability_cache_ttl_seconds = int(config.get("capability_cache_ttl_seconds", 300))
        self.timeout_adjusted = False
        self._provider_events: list[dict[str, Any]] = []
        self._last_native_probe_result: dict[str, Any] | None = None
        self._last_fallback_reason: str | None = None
        self._last_fallback_strategy: str | None = None
        self._last_selected_model: str | None = self.model or None
        self.stream = self._resolve_stream_default(config.get("stream"))

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

    def _resolve_stream_default(self, configured_stream: Any) -> bool:
        if configured_stream is not None:
            return bool(configured_stream)
        return self._is_local_endpoint() and self.stream_local_default

    def _is_local_provider(self) -> bool:
        provider_name = str(self.config.get("provider", ""))
        if provider_name == "local-openai-compatible":
            return True
        return self._is_local_endpoint()

    def _use_lm_studio_compatibility(self) -> bool:
        return self._is_local_provider() and self.lm_studio_compatibility

    def _is_local_endpoint(self) -> bool:
        if not self.base_url:
            return False
        parsed = urlparse(self.base_url)
        host = parsed.hostname or ""
        if host in {"localhost", "127.0.0.1", "host.docker.internal"}:
            return True
        # Treat private / local network IPs as local endpoints
        import ipaddress
        try:
            addr = ipaddress.ip_address(host)
            return addr.is_private or addr.is_loopback
        except ValueError:
            return False

    def _effective_timeout(self) -> float:
        if self._is_local_provider():
            return max(self.timeout, self.local_model_timeout)
        return self.timeout

    def _emit_provider_event(
        self,
        event: str,
        *,
        message: str = "",
        status: str = "info",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        payload = {
            "event": event,
            "action_type": "chat_completion",
            "step": 0,
            "message": Sanitizer.sanitize_text(message),
            "status": status,
            "metadata": Sanitizer.sanitize_data(metadata or {}),
        }
        self._provider_events.append(payload)
        if metadata:
            if metadata.get("fallback_reason"):
                self._last_fallback_reason = str(metadata["fallback_reason"])
            if metadata.get("fallback_strategy"):
                self._last_fallback_strategy = str(metadata["fallback_strategy"])
        if callable(self.event_callback):
            self.event_callback(payload)


    UNSUPPORTED_MEDIA_TYPES = frozenset({"audio_url", "video_url"})

    def _warn_unsupported_media(self, content: Any) -> list[dict[str, Any]]:
        from .multimodal import adapt_content_blocks_for_provider
        if isinstance(content, list):
            content = adapt_content_blocks_for_provider(
                content,
                multimodal_enabled=True
            )
        else:
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

    def _build_chat_paths(self) -> list[str]:
        raise NotImplementedError

    def _build_headers(self) -> dict[str, str]:
        raise NotImplementedError

    def _process_chat_response(self, data: dict[str, Any], tool_mode: str) -> dict[str, Any]:
        raise NotImplementedError

    def _normalize_action_payload(self, action: dict[str, Any]) -> dict[str, Any]:
        valid_types = {
            "plan",
            "read_file",
            "apply_patch",
            "run_shell",
            "run_tests",
            "final",
            "write_file",
            "list_files",
            "replace_content",
            "grep",
            "ast_search",
            "parallel"
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

    def _iter_json_candidates(self, content: str) -> list[str]:
        cleaned = content.strip()
        candidates: list[str] = []

        if "```" in cleaned:
            fence_parts = cleaned.split("```")
            for index in range(1, len(fence_parts), 2):
                block = fence_parts[index].strip()
                if block.startswith("json"):
                    block = block[4:].strip()
                if block:
                    candidates.append(block)

        decoder = json.JSONDecoder()
        for start, char in enumerate(cleaned):
            if char != "{":
                continue
            try:
                obj, end = decoder.raw_decode(cleaned[start:])
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                candidates.append(cleaned[start : start + end])
        return candidates

    def _validate_action_dict(self, action_data: dict[str, Any]) -> str:
        # Single-pass normalization for common model output variations
        # 1. Handle 'action_type' as alias for 'type'
        if "action_type" in action_data and "type" not in action_data:
            action_data["type"] = action_data["action_type"]

        action_type = action_data.get("type")
        if not action_type:
            raise ValueError("schema_validation_failed")

        supported = {
            "plan", "read_file", "apply_patch", "run_shell",
            "run_tests", "parallel", "final", "grep",
            "ast_search", "list_files", "replace_content", "write_file"
        }
        if action_type not in supported:
            raise ValueError("unsupported_action")

        try:
            from pydantic import ValidationError

            # Single-pass: normalize action_type, wrap flat keys, strip meta keys
            if action_type != "parallel" and "payload" not in action_data:
                meta_keys = {"type", "reason", "action_type", "action"}
                payload_keys = set(action_data.keys()) - meta_keys
                if payload_keys:
                    action_data["payload"] = {k: action_data[k] for k in payload_keys}
            # Clean up top-level to avoid pydantic confusion
            for key in list(action_data.keys()):
                if key not in {"type", "reason", "payload"}:
                    del action_data[key]

            validated = AgentActionResponse.model_validate(action_data).root
            action_dict = validated.model_dump()
            normalized = self._normalize_action_payload(action_dict)
            return json.dumps(normalized)
        except ValidationError as exc:
            logger.debug("Schema validation failed for candidate action: %s", exc)
            raise ValueError("schema_validation_failed") from exc

    def _validate_and_transform_action(self, content: str) -> str:
        cleaned = content.strip()
        try:
            direct_payload = json.loads(cleaned)
        except json.JSONDecodeError:
            direct_payload = None
        else:
            if not isinstance(direct_payload, dict):
                raise ValueError("invalid_payload")
            return self._validate_action_dict(direct_payload)

        errors: list[str] = []
        for candidate in self._iter_json_candidates(content):
            try:
                action_data = json.loads(candidate)
            except json.JSONDecodeError:
                errors.append("invalid_json")
                continue
            if not isinstance(action_data, dict):
                errors.append("invalid_payload")
                continue
            try:
                return self._validate_action_dict(action_data)
            except ValueError as exc:
                errors.append(str(exc))
                continue

        logger.error("Invalid JSON action from agent: %s", Sanitizer.sanitize_text(content))
        if "schema_validation_failed" in errors:
            raise ValueError("schema_validation_failed")
        if "unsupported_action" in errors:
            raise ValueError("unsupported_action")
        raise ValueError("invalid_json")

    def _sanitize_response(self, response_data: dict[str, Any]) -> dict[str, Any]:
        return Sanitizer.sanitize_data(response_data)

    def _tool_definitions(self) -> list[dict[str, Any]]:
        schema_map: dict[str, type[BaseModel]] = {
            "plan": PlanPayload,
            "read_file": ReadFilePayload,
            "write_file": WriteFilePayload,
            "list_files": ListFilesPayload,
            "replace_content": ReplaceContentPayload,
            "apply_patch": ApplyPatchPayload,
            "run_shell": RunShellPayload,
            "run_tests": RunTestsPayload,
            "grep": GrepPayload,
            "ast_search": AstSearchPayload,
            "final": FinalPayload,
        }
        descriptions = {
            "plan": "Summarize the next step without changing files.",
            "read_file": "Read one file from the workspace.",
            "write_file": "Write a full file to the workspace.",
            "list_files": "List files in a directory.",
            "replace_content": "Replace existing file content with new content.",
            "apply_patch": "Apply a unified diff patch.",
            "run_shell": "Run a shell command in the workspace sandbox.",
            "run_tests": "Run the test suite or one test target.",
            "grep": "Search text in files.",
            "ast_search": "Search code symbols by AST heuristics.",
            "final": "Finish the task with a summary.",
        }
        return [
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": descriptions[name],
                    "parameters": schema.model_json_schema(),
                },
            }
            for name, schema in schema_map.items()
        ]

    async def resolve_tool_calling_mode(self) -> str:
        if self.tool_calling == "json":
            return "json"

        probe = await self._probe_native_tool_calling()
        self._last_native_probe_result = dict(probe)
        supported = probe.get("supported", False)
        
        if self.tool_calling == "native":
            if not supported:
                from .sanitizer import Sanitizer
                provider_name = getattr(self, "provider", self.__class__.__name__)
                sanitized_url = Sanitizer.sanitize_text(self.base_url)
                msg = (
                    f"Native tool-calling requested but unsupported by {provider_name} "
                    f"model '{self.model}' at {sanitized_url}. "
                    f"supports_native_tool_calling=False, "
                    f"native_tool_calling_probe={probe.get('status', 'unknown')}. "
                    f"Suggestion: use --tool-calling json or --allow-native-tools-for-local "
                    f"if you know the backend supports it."
                )
                raise ValueError(msg)
            return "native"
            
        if self.tool_calling == "auto":
            if self._is_local_provider():
                if self.allow_native_tools_for_local and supported:
                    return "native"
                return "json"
            else:
                return "native" if supported else "json"
                
        return self.tool_calling

    def _is_plain_chat_mode(self) -> bool:
        return bool(self.config.get("plain_chat", False))

    def _message_diagnostics(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        diagnostics: list[dict[str, Any]] = []
        for message in messages:
            content = message.get("content", "")
            if isinstance(content, list):
                content_size = sum(len(str(block)) for block in content)
                content_type = "list"
            else:
                content_size = len(str(content))
                content_type = "text"
            diagnostics.append(
                {
                    "role": message.get("role", "user"),
                    "content_type": content_type,
                    "content_size": content_size,
                    "has_tool_calls": bool(message.get("tool_calls")),
                    "has_tool_call_id": bool(message.get("tool_call_id")),
                }
            )
        return {
            "message_count": len(messages),
            "messages": diagnostics,
        }

    def _simplify_messages_for_local_retry(
        self, messages: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        system_parts: list[str] = []
        simplified: list[dict[str, Any]] = []
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            if isinstance(content, list):
                content = "\n".join(
                    str(block.get("text", "")) for block in content if isinstance(block, dict)
                )
            content_text = Sanitizer.strip_control_chars(str(content))
            if role == "system":
                if content_text:
                    system_parts.append(content_text)
                continue
            if role == "tool":
                simplified.append(
                    {
                        "role": "user",
                        "content": f"Tool result:\n{content_text}",
                    }
                )
                continue
            simplified.append({"role": role, "content": content_text})
        if system_parts:
            simplified.insert(0, {"role": "system", "content": "\n\n".join(system_parts)})
        return simplified

    def _fold_system_into_first_user(
        self, messages: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        system_parts: list[str] = []
        rewritten: list[dict[str, Any]] = []
        injected = False
        for message in messages:
            role = message.get("role", "user")
            if role == "system":
                content = Sanitizer.strip_control_chars(str(message.get("content", "")))
                if content:
                    system_parts.append(content)
                continue
            cloned = dict(message)
            if not injected and role == "user" and system_parts:
                content = Sanitizer.strip_control_chars(str(cloned.get("content", "")))
                cloned["content"] = (
                    "Follow these instructions for this reply:\n"
                    f"{chr(10).join(system_parts)}\n\n"
                    f"User request:\n{content}"
                )
                injected = True
            rewritten.append(cloned)
        if system_parts and not injected:
            rewritten.insert(0, {"role": "user", "content": "\n\n".join(system_parts)})
        return rewritten

    def _build_local_retry_payload(
        self,
        messages: list[dict[str, Any]],
        *,
        fallback_reason: str,
    ) -> dict[str, Any]:
        compatibility_instruction = (
            "Return exactly one JSON object for the next action.\n"
            "Do not include markdown, explanation, or any text before/after the JSON.\n"
            "Use this schema: "
            '{"type":"read_file|write_file|list_files|replace_content|'
            'apply_patch|run_shell|run_tests|grep|ast_search|final|plan",'
            '"payload":{...}}\n'
            'If the task is complete, return {"type":"final","payload":{"message":"..."}}.'
        )
        simplified_messages = self._simplify_messages_for_local_retry(messages)
        if simplified_messages and simplified_messages[0].get("role") == "system":
            current = str(simplified_messages[0].get("content", ""))
            simplified_messages[0]["content"] = f"{compatibility_instruction}\n\n{current}".strip()
        else:
            simplified_messages.insert(0, {"role": "system", "content": compatibility_instruction})
        retry_payload: dict[str, Any] = {
            "model": self.model,
            "messages": simplified_messages,
            "temperature": 0,
            "stream": False,
        }
        max_tokens = self.config.get("max_tokens")
        if max_tokens is not None:
            retry_payload["max_tokens"] = max_tokens
        self._emit_provider_event(
            "llm.local_retry_mode",
            message="Retrying local provider in JSON-compatible mode",
            status="retrying",
            metadata={
                "fallback_reason": fallback_reason,
                "fallback_strategy": "simplified_history_json",
                "stream": False,
                "tool_calling": "json-compatible",
            },
        )
        return retry_payload

    async def _retry_local_compat_mode(
        self,
        *,
        url: str,
        messages: list[dict[str, Any]],
        fallback_reason: str,
        tool_mode: str,
    ) -> dict[str, Any]:
        retry_payload = self._build_local_retry_payload(
            messages,
            fallback_reason=fallback_reason,
        )
        response = await self._request_with_retry(
            "POST", url, json=retry_payload, headers=self._build_headers()
        )
        data = response.json()
        return self._process_chat_response(data, tool_mode)

    async def _iter_sse_data(
        self, response: httpx.Response
    ) -> AsyncIterator[str]:
        buffer: list[str] = []
        async for line in response.aiter_lines():
            if line == "":
                if buffer:
                    yield "\n".join(buffer)
                    buffer = []
                continue
            if line.startswith(":"):
                continue
            if line.startswith("data:"):
                buffer.append(line[5:].lstrip())
                continue
            if line.startswith("event:"):
                continue
            raise ValueError("Malformed streaming response from provider")
        if buffer:
            yield "\n".join(buffer)

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

        effective_timeout = self._effective_timeout()
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(effective_timeout),
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
                except httpx.ReadTimeout as exc:
                    if (
                        self._is_local_provider()
                        and self.auto_increase_timeout
                        and not self.timeout_adjusted
                    ):
                        self.timeout_adjusted = True
                        effective_timeout = max(effective_timeout, self.local_model_timeout)
                        client.timeout = httpx.Timeout(effective_timeout)
                        self._emit_provider_event(
                            "llm.timeout_adjusted",
                            message=(
                                "Local model timed out; retrying once with "
                                f"timeout={effective_timeout:.0f}s"
                            ),
                            status="retrying",
                            metadata={
                                "timeout_adjusted": True,
                                "timeout_seconds": effective_timeout,
                            },
                        )
                        continue
                    suggestion = ""
                    if self._is_local_provider():
                        suggestion = (
                            f" Increase timeout to about {int(self.local_model_timeout)}s "
                            "with --local-model-timeout or enable --auto-increase-timeout."
                        )
                    raise httpx.ReadTimeout(
                        f"Read timeout from provider.{suggestion}",
                        request=exc.request,
                    ) from exc
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

    async def _probe_native_tool_calling(self) -> dict[str, Any]:
        cache_key = f"capability_probe:{self.__class__.__name__}:{self.base_url}:{self.model}"
        now = time.time()

        # 1. Try In-memory cache first
        if cache_key in _PROBE_CACHE:
            entry = _PROBE_CACHE[cache_key]
            if now - entry["timestamp"] < self.capability_cache_ttl_seconds:
                result = entry["result"].copy()
                if result.get("status") != "skipped_by_compat_mode":
                    result["capability_probe_cache_hit"] = True
                    return result

        # 2. Try persistent cache if available
        from .cache import LocalCache as _LocalCache
        cache = self.config.get("cache")
        if isinstance(cache, _LocalCache):
            cached_data = cache.get_json("capabilities", cache_key)
            ts = cached_data.get("timestamp", 0) if cached_data else 0
            if cached_data and (now - ts < self.capability_cache_ttl_seconds):
                result = cached_data["result"]
                if result.get("status") != "skipped_by_compat_mode":
                    result["capability_probe_cache_hit"] = True
                    # Sync back to in-memory for this process
                    _PROBE_CACHE[cache_key] = {"timestamp": cached_data["timestamp"], "result": result}
                    return result

        if not self._is_local_provider():
            result = {
                "supported": self.supports_tool_calling,
                "status": "not_applicable",
            }
            if isinstance(cache, _LocalCache):
                cache.set_json("capabilities", cache_key, {"timestamp": now, "result": result})
            _PROBE_CACHE[cache_key] = {"timestamp": now, "result": result}
            return result

        if (
            self._use_lm_studio_compatibility()
            and not self.allow_native_tools_for_local
            and self.tool_calling != "native"
            and not self.supports_tool_calling
        ):
            return {
                "supported": False,
                "status": "skipped_by_compat_mode",
                "reason": "Native probe disabled by LM Studio compatibility mode",
            }

        # Use full tool definitions to ensure the model can handle the complex schema
        tools = self._tool_definitions()

        probe_payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": "Respond using the 'plan' tool with a short message confirming tool support.",
                }
            ],
            "temperature": 0,
            "stream": False,
            "tools": tools,
            "tool_choice": "auto",
            "max_tokens": 64,
        }

        result: dict[str, Any] = {"supported": False, "status": "unknown"}
        last_exc: Exception | None = None

        for url in self._build_chat_paths():
            try:
                response = await self._request_with_retry(
                    "POST", url, json=probe_payload, headers=self._build_headers()
                )
                response.raise_for_status()
                data = response.json()
                message = {}
                if isinstance(data.get("choices"), list) and data["choices"]:
                    message = data["choices"][0].get("message", {})

                tool_calls = message.get("tool_calls") or []
                if tool_calls:
                    result = {"supported": True, "status": "supported"}
                    break
                if _reasoning_indicates_probe_tool_call(message.get("reasoning_content")):
                    result = {
                        "supported": True,
                        "status": "supported_via_reasoning_fallback",
                        "reason": "Provider emitted probe tool intent in reasoning_content",
                    }
                    break
                else:
                    result = {
                        "supported": False,
                        "status": "not_supported",
                        "reason": "Model returned no tool_calls despite tool_choice=required",
                    }
            except Exception as exc:
                last_exc = exc
                continue

        if not result.get("supported") and last_exc:
            result = {
                "supported": False,
                "status": "probe_failed",
                "reason": Sanitizer.sanitize_text(str(last_exc)),
            }
        
        result["capability_probe_cache_hit"] = False
        if isinstance(cache, _LocalCache):
            cache.set_json("capabilities", cache_key, {"timestamp": now, "result": result})
        _PROBE_CACHE[cache_key] = {"timestamp": now, "result": result}
        return result


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
                "No models returned by "
                f"{self._build_models_url()} for provider "
                f"{self.config.get('provider')}"
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
        self._last_selected_model = selected

        return selected

    async def chat_completion(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        self._validate_config()
        self._provider_events = []
        self._last_fallback_reason = None
        self._last_fallback_strategy = None

        # Warn if reasoning model without max_tokens
        if self.config.get("is_reasoning_model") and self.config.get("max_tokens") is None:
            logger.warning(
                "Reasoning model %s detected without max_tokens set. "
                "This may cause truncated responses. "
                "Set --max-tokens or LLM_HARNESS_MAX_TOKENS to avoid issues.",
                self.model,
            )

        instruction = ""
        if not self._is_plain_chat_mode():
            instruction = (
                "You are a coding agent. Your goal is to solve the task by executing actions.\n"
                "Return EXACTLY one JSON object for each step. "
                "DO NOT include any text outside the JSON.\n"
                "Available actions:\n"
                "- plan: {\"type\":\"plan\", \"payload\":{\"message\":\"...\"}}\n"
                "- read_file: {\"type\":\"read_file\", \"payload\":{\"path\":\"...\"}}\n"
                "- write_file: {\"type\":\"write_file\", "
                "\"payload\":{\"path\":\"...\", \"content\":\"...\"}}\n"
                "- list_files: {\"type\":\"list_files\", \"payload\":{\"path\":\".\"}}\n"
                "- replace_content: {\"type\":\"replace_content\", "
                "\"payload\":{\"path\":\"...\", \"old_content\":\"...\", "
                "\"new_content\":\"...\"}}\n"
                "- apply_patch: {\"type\":\"apply_patch\", \"payload\":{\"diff\":\"...\"}}\n"
                "- run_shell: {\"type\":\"run_shell\", "
                "\"payload\":{\"command\":\"...\", \"timeout\":30}}\n"
                "- run_tests: {\"type\":\"run_tests\", \"payload\":{\"test_path\":\"tests/\"}}\n"
                "- grep: {\"type\":\"grep\", \"payload\":{\"pattern\":\"...\", "
                "\"path\":\".\", \"recursive\":true}}\n"
                "- ast_search: {\"type\":\"ast_search\", "
                "\"payload\":{\"symbol_name\":\"...\", \"path\":\".\"}}\n"
                "- final: {\"type\":\"final\", \"payload\":{\"message\":\"Summary of work\"}}\n\n"
                "Constraints:\n"
                "- No shell redirection (>, >>, |). Use write_file or replace_content instead.\n"
                "- Keep actions small and incremental.\n"
            )
        enriched_messages = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            tool_calls = m.get("tool_calls")
            tool_call_id = m.get("tool_call_id")
            if isinstance(content, list):
                from .multimodal import adapt_content_blocks_for_provider
                adapted_content = adapt_content_blocks_for_provider(
                    content,
                    multimodal_enabled=self.config.get("multimodal", False)
                )
                sanitized_content = []
                for block in adapted_content:
                    if block.get("type") == "text":
                        sanitized_content.append({
                            "type": "text",
                            "text": Sanitizer.strip_control_chars(block.get("text", ""))
                        })
                    else:
                        sanitized_content.append(block)
                enriched_messages.append({"role": role, "content": sanitized_content})
            else:
                entry = {
                    "role": role,
                    "content": Sanitizer.strip_control_chars(str(content))
                }
                if role == "assistant" and isinstance(tool_calls, list):
                    entry["tool_calls"] = tool_calls
                if role == "tool" and tool_call_id:
                    entry["tool_call_id"] = tool_call_id
                enriched_messages.append(entry)
        if instruction:
            if enriched_messages and enriched_messages[0].get("role") == "system":
                current = str(enriched_messages[0].get("content", ""))
                enriched_messages[0]["content"] = f"{instruction}\n\n{current}".strip()
            else:
                enriched_messages.insert(0, {"role": "system", "content": instruction})
        if self._is_plain_chat_mode() and self._is_local_provider():
            enriched_messages = self._fold_system_into_first_user(enriched_messages)

        last_error: Exception | None = None
        local_compat_retry_used = False
        local_semantic_retry_used = False
        
        resolved_tool_mode = await self.resolve_tool_calling_mode()
        
        for url in self._build_chat_paths():
            try:
                tool_mode = "plain" if self._is_plain_chat_mode() else resolved_tool_mode
                payload = {
                    "model": self.model,
                    "messages": enriched_messages,
                    "temperature": 0,
                    "stream": self.stream,
                }
                max_tokens = self.config.get("max_tokens")
                if max_tokens is not None:
                    payload["max_tokens"] = max_tokens
                if tool_mode == "native":
                    payload["tools"] = self._tool_definitions()
                    payload["tool_choice"] = "auto"
                # Check per-model cache before sending response_format
                rf_cache_key = f"response_format:{self.model}"
                rf_supported = _RESPONSE_FORMAT_CACHE.get(
                    rf_cache_key, self._supports_response_format
                )
                if tool_mode == "json" and not self.stream and rf_supported:
                    payload["response_format"] = {"type": "json_object"}

                if self.stream:
                    # Request usage in final chunk when provider supports it
                    payload["stream_options"] = {"include_usage": True}
                    return await self._chat_completion_stream(url, payload, tool_mode)

                response = await self._request_with_retry(
                    "POST", url, json=payload, headers=self._build_headers()
                )
                data = response.json()
                return self._process_chat_response(data, tool_mode)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    last_error = exc
                    continue
                if (
                    exc.response.status_code == 400
                    and self._is_local_provider()
                    and not local_compat_retry_used
                ):
                    local_compat_retry_used = True
                    fallback_reason = "http_400_local_provider"
                    diagnostic = self._message_diagnostics(enriched_messages)
                    self._emit_provider_event(
                        "llm.local_400_retry",
                        message="Local provider rejected request; retrying with simplified history",
                        status="retrying",
                        metadata={
                            **diagnostic,
                            "tool_mode": tool_mode,
                            "stream": self.stream,
                        },
                    )
                    logger.warning(
                        "Local provider returned 400; retrying with simplified history: %s",
                        Sanitizer.sanitize_data(diagnostic),
                    )
                    retry_payload = self._build_local_retry_payload(
                        enriched_messages,
                        fallback_reason=fallback_reason,
                    )
                    try:
                        response = await self._request_with_retry(
                            "POST", url, json=retry_payload, headers=self._build_headers()
                        )
                        data = response.json()
                        return self._process_chat_response(data, tool_mode)
                    except httpx.HTTPStatusError as retry_exc:
                        logger.warning(
                            "Local provider compatibility retry failed with status=%s",
                            retry_exc.response.status_code,
                        )
                        raise
                if exc.response.status_code == 400 and self._supports_response_format:
                    self._supports_response_format = False
                    rf_cache_key = f"response_format:{self.model}"
                    _RESPONSE_FORMAT_CACHE[rf_cache_key] = False
                    logger.debug(
                        "Provider rejected response_format=json_object; "
                        "cached as unsupported for model %s",
                        self.model,
                    )
                    try:
                        payload = {
                            "model": self.model,
                            "messages": enriched_messages,
                            "temperature": 0,
                        }
                        if tool_mode == "native":
                            payload["tools"] = self._tool_definitions()
                            payload["tool_choice"] = "auto"
                        max_tokens = self.config.get("max_tokens")
                        if max_tokens is not None:
                            payload["max_tokens"] = max_tokens
                        response = await self._request_with_retry(
                            "POST", url, json=payload, headers=self._build_headers()
                        )
                        data = response.json()
                        return self._process_chat_response(data, tool_mode)
                    except Exception as fallback_exc:
                        last_error = fallback_exc
                        raise
                raise
            except ValueError as exc:
                if (
                    self._is_local_provider()
                    and not self._is_plain_chat_mode()
                    and not local_semantic_retry_used
                    and self.tool_calling != "native"
                    and str(exc)
                    in {
                        "schema_validation_failed",
                        "invalid_json",
                        "Provider returned empty content",
                    }
                ):
                    local_semantic_retry_used = True
                    logger.warning(
                        "Local provider returned non-compatible action payload; "
                        "retrying in compatibility mode: %s",
                        str(exc),
                    )
                    try:
                        return await self._retry_local_compat_mode(
                            url=url,
                            messages=enriched_messages,
                            fallback_reason=f"semantic_retry:{exc}",
                            tool_mode=tool_mode,
                        )
                    except Exception as retry_exc:
                        last_error = retry_exc
                        raise
                last_error = exc
                raise
        raise ValueError(
            "OpenAI-compatible provider did not expose a supported endpoint"
        ) from last_error

    async def _chat_completion_stream(
        self, url: str, payload: dict[str, Any], tool_mode: str
    ) -> dict[str, Any]:
        full_content = ""
        reasoning_content = ""
        usage: dict[str, Any] = {"total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0}
        tool_calls: dict[int, dict[str, Any]] = {}

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(self._effective_timeout()), transport=self.transport
        ) as client:
            headers = self._build_headers()
            async with client.stream("POST", url, json=payload, headers=headers) as response:
                response.raise_for_status()
                async for data_str in self._iter_sse_data(response):
                    if data_str == "[DONE]":
                        break

                    try:
                        chunk = json.loads(data_str)
                        choices = chunk.get("choices")
                        if not choices:
                            if chunk.get("usage"):
                                usage = chunk["usage"]
                            continue
                        delta = choices[0].get("delta", {})
                        if "content" in delta:
                            full_content += delta["content"]
                            self._emit_provider_event(
                                "llm.delta",
                                message=delta["content"] if self.verbose_stream else "",
                                status="streaming",
                            )
                        elif "reasoning_content" in delta:
                            reasoning_content += delta["reasoning_content"]
                            self._emit_provider_event(
                                "llm.reasoning_delta",
                                message=delta["reasoning_content"] if self.verbose_stream else "",
                                status="streaming",
                            )
                        for tool_delta in delta.get("tool_calls", []):
                            index = int(tool_delta.get("index", 0))
                            current = tool_calls.setdefault(
                            index,
                            {
                                "id": tool_delta.get("id"),
                                "type": "function",
                                "function": {"name": "", "arguments": ""},
                            },
                        )
                            function = tool_delta.get("function", {})
                            if function.get("name"):
                                current["function"]["name"] = function["name"]
                            if function.get("arguments"):
                                current["function"]["arguments"] += function["arguments"]
                            if tool_delta.get("id"):
                                current["id"] = tool_delta["id"]

                        if chunk.get("usage"):
                            usage = chunk["usage"]
                    except json.JSONDecodeError:
                        raise ValueError("Malformed streaming response from provider") from None

        # If no explicit content but reasoning exists, fall back to reasoning as content
        if not full_content and reasoning_content:
            full_content = reasoning_content

        data = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": full_content,
                        "tool_calls": [tool_calls[index] for index in sorted(tool_calls)],
                    }
                }
            ],
            "usage": usage,
        }
        if reasoning_content:
            data.setdefault("_provider_meta", {})
            data["_provider_meta"]["reasoning_content"] = reasoning_content
        self._emit_provider_event(
            "llm.completed",
            status="completed",
            metadata={"reasoning_chars": len(reasoning_content)},
        )
        return self._process_chat_response(data, tool_mode)

    def _process_chat_response(self, data: dict[str, Any], tool_mode: str) -> dict[str, Any]:
        data.setdefault("_provider_meta", {})
        data["_provider_meta"]["timeout_adjusted"] = self.timeout_adjusted
        data["_provider_meta"]["event_log"] = list(self._provider_events)
        data["_provider_meta"]["final_tool_calling_mode"] = tool_mode
        data["_provider_meta"]["selected_model"] = self._last_selected_model or self.model
        data["_provider_meta"]["lm_studio_compatibility"] = self._use_lm_studio_compatibility()
        if self._last_native_probe_result is not None:
            data["_provider_meta"]["supports_native_tool_calling"] = bool(
                self._last_native_probe_result.get("supported", False)
            )
            data["_provider_meta"]["native_tool_calling_probe"] = self._last_native_probe_result
        if self._last_fallback_reason:
            data["_provider_meta"]["fallback_reason"] = self._last_fallback_reason
        if self._last_fallback_strategy:
            data["_provider_meta"]["fallback_strategy"] = self._last_fallback_strategy
        msg = {}
        if isinstance(data.get("choices"), list) and len(data["choices"]) > 0:
            msg = data["choices"][0].get("message", {})

        tool_calls = msg.get("tool_calls") or []
        if self._is_plain_chat_mode():
            usage = data.get("usage", {})
            if not usage:
                data["usage"] = {"total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0}
            return self._sanitize_response(data)
        if tool_mode == "native" and tool_calls:
            for tool_call in tool_calls:
                function = tool_call.get("function") or {}
                name = function.get("name")
                raw_arguments = function.get("arguments", "{}")
                if name not in {tool["function"]["name"] for tool in self._tool_definitions()}:
                    raise ValueError(f"Unknown tool_call received: {name}")
                try:
                    parsed_arguments = (
                        json.loads(raw_arguments)
                        if isinstance(raw_arguments, str)
                        else raw_arguments
                    )
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid tool_call arguments for {name}") from exc
                if not isinstance(parsed_arguments, dict):
                    raise ValueError(f"Invalid tool_call arguments for {name}")
                self._validate_action_dict({"type": name, "payload": parsed_arguments})
            usage = data.get("usage", {})
            if not usage:
                data["usage"] = {"total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0}
            return self._sanitize_response(data)

        reasoning_content = ""
        content = ""
        if isinstance(data.get("choices"), list) and len(data["choices"]) > 0:
            raw = msg.get("content") or ""
            reasoning_raw = msg.get("reasoning_content") or ""
            if raw:
                content = str(raw)
                reasoning_content = str(reasoning_raw) if reasoning_raw else ""
            elif reasoning_raw:
                reasoning_content = str(reasoning_raw)

        if reasoning_content:
            data.setdefault("_provider_meta", {})
            data["_provider_meta"]["reasoning_content"] = reasoning_content
            truncated = (
                reasoning_content[:200] + "..."
                if len(reasoning_content) > 200
                else reasoning_content
            )
            logger.debug(
                "Reasoning content (%d chars): %s",
                len(reasoning_content),
                truncated,
            )
            # Auto-detect reasoning model on first response with reasoning_content
            if not getattr(self, "_detected_reasoning_model", False):
                self._detected_reasoning_model = True
                self.config["is_reasoning_model"] = True
                logger.info(
                    "Auto-detected reasoning model %s from reasoning_content",
                    self.model,
                )

        if not tool_calls and reasoning_content and self._use_lm_studio_compatibility():
            synthesized_tool_call = _extract_textual_tool_call(reasoning_content)
            if synthesized_tool_call:
                tool_calls = [synthesized_tool_call]
                msg["tool_calls"] = tool_calls
                data["choices"][0]["message"]["tool_calls"] = tool_calls
                data["_provider_meta"]["tool_calls_synthesized_from_reasoning"] = True
                data["_provider_meta"]["fallback_reason"] = "reasoning_tool_call_extracted"
                data["_provider_meta"]["fallback_strategy"] = "lm_studio_textual_tool_call"

        if not content:
            if tool_calls and self.tool_calling in ("auto", "native"):
                return self._sanitize_response(data)
            if reasoning_content:
                content = reasoning_content
            else:
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
        if self.model:
            self._last_selected_model = self.model
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
        self.supports_tool_calling = bool(config.get("supports_tool_calling", False))

    def _validate_config(self):
        # Override to bypass API key requirement for local development models (Ollama, LM Studio)
        self.agent_helper.validate_config()

    def _build_chat_paths(self) -> list[str]:
        # Local providers (LM Studio, Ollama) only support /v1/chat/completions.
        # Skip /v1/responses to avoid 400 Bad Request on probe.
        base = self.base_url
        if base.endswith("/v1"):
            return [f"{base}/chat/completions"]
        if base.endswith("/chat/completions"):
            return [base]
        return [f"{base}/v1/chat/completions"]


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
        self._last_selected_model = selected_model
        native_probe = await self._probe_native_tool_calling()
        self._last_native_probe_result = dict(native_probe)
        return {
            "status": "healthy",
            "provider": "local-openai-compatible",
            "details": {
                "models_url": self._build_models_url(),
                "available_models": self._available_models or [],
                "selected_model": selected_model,
                "supports_response_format": self._supports_response_format,
                "supports_native_tool_calling": native_probe.get("supported", False),
                "native_tool_calling_probe": native_probe,
                "lm_studio_compatibility": self._use_lm_studio_compatibility(),
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
        # Enforce multimodal configuration check
        for m in messages:
            content = m.get("content", "")
            if isinstance(content, list):
                has_image = any(
                    isinstance(b, dict) and b.get("type") == "image_url"
                    for b in content
                )
                if has_image and not self.config.get("multimodal", False):
                    raise ValueError(
                        "Provider or model does not support multimodal input. "
                        "Enable 'multimodal' or choose a multimodal model."
                    )
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
        # Enforce multimodal configuration check
        for m in messages:
            content = m.get("content", "")
            if isinstance(content, list):
                has_image = any(
                    isinstance(b, dict) and b.get("type") == "image_url"
                    for b in content
                )
                if has_image and not self.config.get("multimodal", False):
                    raise ValueError(
                        "Provider or model does not support multimodal input. "
                        "Enable 'multimodal' or choose a multimodal model."
                    )
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
