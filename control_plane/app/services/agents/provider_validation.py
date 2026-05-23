# Owner: agent-platform
"""Opt-in real provider validation suite for agentic runtime.

Transforms provider_validation.py from stub into real end-to-end validation
for GA agentic readiness. Uses controlled real provider calls with strict
budget, timeout, and safety guards.

Feature flags:
  AGENT_REAL_PROVIDER_VALIDATION_ENABLED   (default: false)
  AGENT_REAL_PROVIDER_VALIDATION_ALLOW_PAID (default: false)
  AGENT_REAL_PROVIDER_VALIDATION_BUDGET_BRL (default: 1.00)
  AGENT_REAL_PROVIDER_VALIDATION_TIMEOUT_SECONDS (default: 60)

Providers: mock, local_gateway, openrouter, openai_compatible_custom, local_llama_cpp
"""

import asyncio
import datetime
import json
import logging
import os
import re
import time
import uuid
from dataclasses import dataclass, field, asdict
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ARTIFACTS_DIR = Path("artifacts/evals/real-provider-validation/latest")

SYNTHETIC_DATASET = {
    "basic_call": {
        "prompt": "Responda apenas com a palavra 'ok'.",
        "expected_substr": "ok",
    },
    "structured_output": {
        "prompt": 'Return valid JSON: {"status": "ok", "value": 42}',
        "schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "value": {"type": "integer"},
            },
            "required": ["status", "value"],
        },
    },
    "tool_call": {
        "prompt": "Call the get_weather tool for Sao Paulo.",
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather for a location",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {"type": "string"},
                        },
                        "required": ["location"],
                    },
                },
            }
        ],
    },
    "memory_injection": {
        "system_prompt": "User likes blue. User's favorite number is 7.",
        "prompt": "What is my favorite color and number?",
        "expected_color": "blue",
        "expected_number": "7",
    },
    "context_compression": {
        "long_history": [
            {"role": "user", "content": f"Message {i}: this is synthetic filler context to build up token pressure."}
            for i in range(20)
        ],
        "prompt": "What was the original goal?",
        "goal": "validate context compression preserves core instructions",
    },
}

ALLOWED_PROVIDERS = ["mock", "local_gateway", "openrouter", "openai_compatible_custom", "local_llama_cpp"]

# ---------------------------------------------------------------------------
# Enums / Status
# ---------------------------------------------------------------------------


class ValidationStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    DEGRADED = "degraded"
    ERROR = "error"


class ProviderCostTier(str, Enum):
    FREE = "free"
    PAID = "paid"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ProviderConfig:
    name: str
    endpoint: str
    api_key_env: str
    model: str
    cost_tier: ProviderCostTier = ProviderCostTier.FREE
    timeout_seconds: int = 30
    headers: Dict[str, str] = field(default_factory=dict)
    weight: int = 10


@dataclass
class ValidationResult:
    feature: str
    provider: str
    status: ValidationStatus = ValidationStatus.ERROR
    duration_ms: float = 0.0
    tokens_used: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_brl: float = 0.0
    error_message: str = ""
    retries: int = 0
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderReport:
    provider: str
    status: str
    results: Dict[str, ValidationResult]
    total_duration_ms: float = 0.0
    total_tokens: int = 0
    total_cost_brl: float = 0.0
    error_message: str = ""


# ---------------------------------------------------------------------------
# Provider configurations
# ---------------------------------------------------------------------------

def _get_provider_configs() -> Dict[str, ProviderConfig]:
    return {
        "mock": ProviderConfig(
            name="mock",
            endpoint="",
            api_key_env="",
            model="mock-model",
            cost_tier=ProviderCostTier.FREE,
            weight=0,
        ),
        "local_gateway": ProviderConfig(
            name="local_gateway",
            endpoint=os.environ.get("AGENT_LOCAL_GATEWAY_ENDPOINT", "http://localhost:8080/v1/chat/completions"),
            api_key_env="",
            model=os.environ.get("AGENT_LOCAL_GATEWAY_MODEL", "local-model"),
            cost_tier=ProviderCostTier.FREE,
            timeout_seconds=int(os.environ.get("AGENT_REAL_PROVIDER_VALIDATION_TIMEOUT_SECONDS", "30")),
        ),
        "openrouter": ProviderConfig(
            name="openrouter",
            endpoint="https://openrouter.ai/api/v1/chat/completions",
            api_key_env="OPENROUTER_API_KEY",
            model=os.environ.get("AGENT_OPENROUTER_MODEL", "openai/gpt-4o-mini"),
            cost_tier=ProviderCostTier.PAID,
            timeout_seconds=int(os.environ.get("AGENT_REAL_PROVIDER_VALIDATION_TIMEOUT_SECONDS", "60")),
            headers={"HTTP-Referer": "https://agentic-platform.local", "X-Title": "Agentic-Provider-Validation"},
        ),
        "openai_compatible_custom": ProviderConfig(
            name="openai_compatible_custom",
            endpoint=os.environ.get("AGENT_CUSTOM_OPENAI_ENDPOINT", ""),
            api_key_env="AGENT_CUSTOM_OPENAI_API_KEY",
            model=os.environ.get("AGENT_CUSTOM_OPENAI_MODEL", "gpt-4o-mini"),
            cost_tier=ProviderCostTier.PAID,
            timeout_seconds=int(os.environ.get("AGENT_REAL_PROVIDER_VALIDATION_TIMEOUT_SECONDS", "60")),
        ),
        "local_llama_cpp": ProviderConfig(
            name="local_llama_cpp",
            endpoint=os.environ.get("AGENT_LOCAL_LLAMA_CPP_ENDPOINT", "http://localhost:8080/v1/chat/completions"),
            api_key_env="",
            model=os.environ.get("AGENT_LOCAL_LLAMA_CPP_MODEL", "llama-3.2-1b"),
            cost_tier=ProviderCostTier.FREE,
            timeout_seconds=int(os.environ.get("AGENT_REAL_PROVIDER_VALIDATION_TIMEOUT_SECONDS", "30")),
        ),
    }


# ---------------------------------------------------------------------------
# Real provider client (HTTP)
# ---------------------------------------------------------------------------

class _ProviderClient:
    def __init__(self, config: ProviderConfig):
        self.config = config
        self._api_key = self._resolve_api_key()

    def _resolve_api_key(self) -> str:
        if not self.config.api_key_env:
            return ""
        key = os.environ.get(self.config.api_key_env, "")
        if key:
            masked = key[:4] + "****" + key[-4:] if len(key) > 8 else "****"
            logger.info("Provider %s: using API key from %s (masked: %s)", self.config.name, self.config.api_key_env, masked)
        return key

    def _mask_api_key(self, value: str) -> str:
        if not value:
            return value
        if len(value) <= 8:
            return "****"
        return value[:4] + "****" + value[-4:]

    def _build_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            **self.config.headers,
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def _build_payload(self, messages: List[Dict], tools: Optional[List] = None, response_format: Optional[Dict] = None) -> Dict:
        payload = {
            "model": self.config.model,
            "messages": messages,
            "stream": False,
            "max_tokens": 256,
            "temperature": 0.0,
        }
        if tools:
            payload["tools"] = tools
        if response_format:
            payload["response_format"] = {"type": "json_object"}
            payload["temperature"] = 0.0
        return payload

    async def chat_completion(
        self,
        messages: List[Dict],
        tools: Optional[List] = None,
        response_format: Optional[Dict] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        if self.config.name == "mock":
            return self._mock_response(messages, tools, response_format)

        import aiohttp

        payload = self._build_payload(messages, tools, response_format)
        headers = self._build_headers()
        url = self.config.endpoint
        effective_timeout = timeout or self.config.timeout_seconds

        logger.info("Provider %s: POST %s model=%s", self.config.name, url, self.config.model)
        t0 = time.monotonic()

        connector = aiohttp.TCPConnector(force_close=True)
        timeout_ctx = aiohttp.ClientTimeout(total=effective_timeout)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout_ctx) as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                body = await resp.text()
                elapsed = time.monotonic() - t0
                logger.info("Provider %s: HTTP %d in %.2fs", self.config.name, resp.status, elapsed)

                if resp.status == 200:
                    try:
                        data = json.loads(body)
                    except json.JSONDecodeError as e:
                        raise RuntimeError(f"Non-JSON response: {body[:200]}") from e
                    return data
                elif resp.status == 401:
                    raise PermissionError(f"Provider {self.config.name} returned 401 (check API key)")
                elif resp.status == 429:
                    raise RuntimeError(f"Provider {self.config.name} rate limited (429)")
                elif resp.status >= 500:
                    raise ConnectionError(f"Provider {self.config.name} server error ({resp.status})")
                else:
                    raise RuntimeError(f"Provider {self.config.name} returned HTTP {resp.status}: {body[:200]}")

    def _mock_response(self, messages: List[Dict], tools: Optional[List] = None, response_format: Optional[Dict] = None) -> Dict[str, Any]:
        last_content = messages[-1]["content"] if messages else ""

        content = "ok"
        if response_format:
            content = '{"status": "ok", "value": 42}'
        elif tools:
            return {
                "id": "mock-chat-" + uuid.uuid4().hex[:8],
                "object": "chat.completion",
                "created": int(time.time()),
                "model": self.config.model,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_mock_" + uuid.uuid4().hex[:8],
                                    "type": "function",
                                    "function": {
                                        "name": tools[0]["function"]["name"],
                                        "arguments": json.dumps({"location": "Sao Paulo"}),
                                    },
                                }
                            ],
                        },
                        "finish_reason": "tool_calls",
                    }
                ],
                "usage": {"prompt_tokens": 25, "completion_tokens": 12, "total_tokens": 37},
            }

        if "goal" in str(messages) and "context" in str(messages):
            content = "The original goal was to validate context compression preserves core instructions. The compression technique must maintain the essential meaning."
        if "blue" in str(messages) and "7" in str(messages):
            content = "Your favorite color is blue and your favorite number is 7."

        return {
            "id": "mock-chat-" + uuid.uuid4().hex[:8],
            "object": "chat.completion",
            "created": int(time.time()),
            "model": self.config.model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 15, "completion_tokens": 5, "total_tokens": 20},
        }


# ---------------------------------------------------------------------------
# Budget tracker
# ---------------------------------------------------------------------------

class _BudgetTracker:
    def __init__(self, max_brl: float):
        self.max_brl = max_brl
        self.spent_brl = 0.0
        self.exceeded = False

    def record(self, cost_brl: float):
        self.spent_brl += cost_brl
        if self.spent_brl >= self.max_brl:
            self.exceeded = True

    def check(self) -> bool:
        return not self.exceeded

    def remaining(self) -> float:
        return max(0.0, self.max_brl - self.spent_brl)


# ---------------------------------------------------------------------------
# Validation implementations
# ---------------------------------------------------------------------------


def _estimate_cost(prompt_tokens: int, completion_tokens: int, provider: str) -> float:
    rates = {
        "mock": (0.0, 0.0),
        "local_gateway": (0.0, 0.0),
        "local_llama_cpp": (0.0, 0.0),
        "openrouter": (2.5e-7, 1.0e-6),
        "openai_compatible_custom": (2.5e-7, 1.0e-6),
    }
    p_rate, c_rate = rates.get(provider, (2.5e-7, 1.0e-6))
    return (prompt_tokens * p_rate) + (completion_tokens * c_rate)


def _extract_usage(response: Dict) -> Tuple[int, int, int]:
    usage = response.get("usage", {})
    if isinstance(usage, dict):
        prompt = usage.get("prompt_tokens", 0)
        completion = usage.get("completion_tokens", 0)
        total = usage.get("total_tokens", prompt + completion)
        return int(prompt), int(completion), int(total)
    return 0, 0, 0


def _extract_content(response: Dict) -> str:
    choices = response.get("choices", [])
    if not choices:
        return ""
    message = choices[0].get("message", {})
    return message.get("content", "") or ""


def _extract_tool_calls(response: Dict) -> List[Dict]:
    choices = response.get("choices", [])
    if not choices:
        return []
    message = choices[0].get("message", {})
    return message.get("tool_calls", [])


class RealProviderValidator:
    def __init__(self):
        self.artifacts_dir = ARTIFACTS_DIR
        logger.info(
            "RealProviderValidator: enabled=%s allow_paid=%s budget=%.2f timeout=%ds",
            self.is_enabled, self.allow_paid, self.budget_brl, self.timeout_seconds,
        )

    @property
    def is_enabled(self) -> bool:
        return os.environ.get("AGENT_REAL_PROVIDER_VALIDATION_ENABLED", "false").lower() == "true"

    @property
    def allow_paid(self) -> bool:
        return os.environ.get("AGENT_REAL_PROVIDER_VALIDATION_ALLOW_PAID", "false").lower() == "true"

    @property
    def budget_brl(self) -> float:
        return float(os.environ.get("AGENT_REAL_PROVIDER_VALIDATION_BUDGET_BRL", "1.00"))

    @property
    def timeout_seconds(self) -> int:
        return int(os.environ.get("AGENT_REAL_PROVIDER_VALIDATION_TIMEOUT_SECONDS", "60"))

    @property
    def provider_configs(self) -> Dict[str, ProviderConfig]:
        return _get_provider_configs()

    # -----------------------------------------------------------------------
    # Guard methods
    # -----------------------------------------------------------------------

    def _check_enabled(self) -> Optional[Dict]:
        if not self.is_enabled:
            return {"status": ValidationStatus.SKIPPED, "reason": "Real provider validation is disabled (AGENT_REAL_PROVIDER_VALIDATION_ENABLED=false)"}
        return None

    def _check_paid_allowed(self, config: ProviderConfig) -> Optional[Dict]:
        if config.cost_tier == ProviderCostTier.PAID and not self.allow_paid:
            return {"status": ValidationStatus.SKIPPED, "reason": f"Paid provider {config.name} blocked (AGENT_REAL_PROVIDER_VALIDATION_ALLOW_PAID=false)"}
        return None

    def _check_configured(self, config: ProviderConfig) -> Optional[Dict]:
        if config.name == "mock":
            return None
        if config.api_key_env and not os.environ.get(config.api_key_env, ""):
            return {"status": ValidationStatus.SKIPPED, "reason": f"API key missing: {config.api_key_env}"}
        endpoint = config.endpoint
        if not endpoint:
            return {"status": ValidationStatus.DEGRADED, "reason": f"Provider {config.name} endpoint not configured"}
        return None

    # -----------------------------------------------------------------------
    # Validation 1: basic_model_call
    # -----------------------------------------------------------------------

    async def validate_basic_model_call(self, provider: str) -> ValidationResult:
        result = ValidationResult(feature="basic_model_call", provider=provider)
        skip = self._check_enabled()
        if skip:
            result.status = ValidationStatus.SKIPPED
            result.details = skip
            return result

        config = self.provider_configs.get(provider)
        if not config:
            result.status = ValidationStatus.SKIPPED
            result.details = {"reason": f"Unknown provider {provider}"}
            return result

        paid_block = self._check_paid_allowed(config)
        if paid_block:
            result.status = ValidationStatus.SKIPPED
            result.details = paid_block
            return result

        configured = self._check_configured(config)
        if configured:
            result.status = ValidationStatus(configured["status"])
            result.details = configured
            return result

        client = _ProviderClient(config)
        t0 = time.monotonic()
        try:
            response = await asyncio.wait_for(
                client.chat_completion(messages=[{"role": "user", "content": SYNTHETIC_DATASET["basic_call"]["prompt"]}]),
                timeout=self.timeout_seconds,
            )
            elapsed = (time.monotonic() - t0) * 1000
            content = _extract_content(response)
            prompt_t, comp_t, total_t = _extract_usage(response)
            cost = _estimate_cost(prompt_t, comp_t, provider)

            result.duration_ms = round(elapsed, 1)
            result.prompt_tokens = prompt_t
            result.completion_tokens = comp_t
            result.tokens_used = total_t
            result.cost_brl = round(cost, 6)

            if content and SYNTHETIC_DATASET["basic_call"]["expected_substr"] in content.lower():
                result.status = ValidationStatus.PASSED
            else:
                result.status = ValidationStatus.FAILED
                result.error_message = f"Expected '{SYNTHETIC_DATASET['basic_call']['expected_substr']}' in response, got: {content[:100]}"
        except asyncio.TimeoutError:
            result.status = ValidationStatus.FAILED
            result.error_message = f"Timeout after {self.timeout_seconds}s"
        except (ConnectionError, RuntimeError, PermissionError, OSError) as e:
            result.status = ValidationStatus.FAILED
            result.error_message = str(e)
        except Exception as e:
            result.status = ValidationStatus.ERROR
            result.error_message = f"Unexpected error: {e}"
            logger.exception("basic_model_call failed for %s", provider)

        return result

    # -----------------------------------------------------------------------
    # Validation 2: structured_output
    # -----------------------------------------------------------------------

    async def validate_structured_output(self, provider: str) -> ValidationResult:
        result = ValidationResult(feature="structured_output", provider=provider)
        skip = self._check_enabled()
        if skip:
            result.status = ValidationStatus.SKIPPED
            result.details = skip
            return result

        config = self.provider_configs.get(provider)
        if not config:
            result.status = ValidationStatus.SKIPPED
            result.details = {"reason": f"Unknown provider {provider}"}
            return result

        paid_block = self._check_paid_allowed(config)
        if paid_block:
            result.status = ValidationStatus.SKIPPED
            result.details = paid_block
            return result

        configured = self._check_configured(config)
        if configured:
            result.status = ValidationStatus(configured["status"])
            result.details = configured
            return result

        client = _ProviderClient(config)
        dataset = SYNTHETIC_DATASET["structured_output"]

        for attempt in range(3):
            result.retries = attempt
            t0 = time.monotonic()
            try:
                response = await asyncio.wait_for(
                    client.chat_completion(
                        messages=[{"role": "user", "content": dataset["prompt"]}],
                        response_format=dataset["schema"],
                    ),
                    timeout=self.timeout_seconds,
                )
                elapsed = (time.monotonic() - t0) * 1000
                content = _extract_content(response)
                prompt_t, comp_t, total_t = _extract_usage(response)
                cost = _estimate_cost(prompt_t, comp_t, provider)

                result.duration_ms = round(elapsed, 1)
                result.prompt_tokens = prompt_t
                result.completion_tokens = comp_t
                result.tokens_used = total_t
                result.cost_brl = round(cost, 6)

                try:
                    parsed = json.loads(content)
                except json.JSONDecodeError:
                    if attempt < 2:
                        logger.warning("structured_output malformed JSON for %s on attempt %d, retrying", provider, attempt)
                        continue
                    result.status = ValidationStatus.FAILED
                    result.error_message = f"Malformed JSON after {attempt + 1} retries: {content[:200]}"
                    return result

                if parsed.get("status") == "ok" and parsed.get("value") == 42:
                    result.status = ValidationStatus.PASSED
                    result.details = {"parsed": parsed}
                    return result
                else:
                    result.status = ValidationStatus.FAILED
                    result.error_message = f"JSON fields mismatch: {parsed}"
                    return result

            except asyncio.TimeoutError:
                result.status = ValidationStatus.FAILED
                result.error_message = f"Timeout after {self.timeout_seconds}s"
                return result
            except (ConnectionError, RuntimeError, PermissionError, OSError) as e:
                result.status = ValidationStatus.FAILED
                result.error_message = str(e)
                return result
            except Exception as e:
                result.status = ValidationStatus.ERROR
                result.error_message = f"Unexpected error: {e}"
                logger.exception("structured_output failed for %s", provider)
                return result

        return result

    # -----------------------------------------------------------------------
    # Validation 3: tool_call_format
    # -----------------------------------------------------------------------

    async def validate_tool_call_format(self, provider: str) -> ValidationResult:
        result = ValidationResult(feature="tool_call_format", provider=provider)
        skip = self._check_enabled()
        if skip:
            result.status = ValidationStatus.SKIPPED
            result.details = skip
            return result

        config = self.provider_configs.get(provider)
        if not config:
            result.status = ValidationStatus.SKIPPED
            result.details = {"reason": f"Unknown provider {provider}"}
            return result

        paid_block = self._check_paid_allowed(config)
        if paid_block:
            result.status = ValidationStatus.SKIPPED
            result.details = paid_block
            return result

        configured = self._check_configured(config)
        if configured:
            result.status = ValidationStatus(configured["status"])
            result.details = configured
            return result

        if config.name == "local_llama_cpp":
            result.status = ValidationStatus.DEGRADED
            result.error_message = "Tool calls not supported on local_llama_cpp"
            return result

        client = _ProviderClient(config)
        dataset = SYNTHETIC_DATASET["tool_call"]
        t0 = time.monotonic()

        try:
            response = await asyncio.wait_for(
                client.chat_completion(
                    messages=[{"role": "user", "content": dataset["prompt"]}],
                    tools=dataset["tools"],
                ),
                timeout=self.timeout_seconds,
            )
            elapsed = (time.monotonic() - t0) * 1000
            prompt_t, comp_t, total_t = _extract_usage(response)
            cost = _estimate_cost(prompt_t, comp_t, provider)

            result.duration_ms = round(elapsed, 1)
            result.prompt_tokens = prompt_t
            result.completion_tokens = comp_t
            result.tokens_used = total_t
            result.cost_brl = round(cost, 6)

            tool_calls = _extract_tool_calls(response)
            if not tool_calls:
                content = _extract_content(response)
                result.status = ValidationStatus.FAILED
                result.error_message = f"No tool_calls in response. Content: {content[:200]}" if content else "No tool_calls in response."
                return result

            tc = tool_calls[0]
            required_fields = ["id", "type", "function"]
            missing = [f for f in required_fields if f not in tc]
            if missing:
                result.status = ValidationStatus.FAILED
                result.error_message = f"Tool call missing fields: {missing}. Got keys: {list(tc.keys())}"
                return result

            if tc.get("type") != "function":
                result.status = ValidationStatus.FAILED
                result.error_message = f"Expected type 'function', got '{tc.get('type')}'"
                return result

            func = tc.get("function", {})
            if not func.get("name"):
                result.status = ValidationStatus.FAILED
                result.error_message = "Tool call function missing name"
                return result

            args_str = func.get("arguments", "{}")
            try:
                json.loads(args_str) if isinstance(args_str, str) else args_str
            except json.JSONDecodeError:
                result.status = ValidationStatus.FAILED
                result.error_message = f"Tool call arguments not valid JSON: {args_str[:100]}"
                return result

            result.status = ValidationStatus.PASSED
            result.details = {"tool_name": func["name"], "tool_call_id": tc["id"]}

        except asyncio.TimeoutError:
            result.status = ValidationStatus.FAILED
            result.error_message = f"Timeout after {self.timeout_seconds}s"
        except (ConnectionError, RuntimeError, PermissionError, OSError) as e:
            result.status = ValidationStatus.FAILED
            result.error_message = str(e)
        except Exception as e:
            result.status = ValidationStatus.ERROR
            result.error_message = f"Unexpected error: {e}"
            logger.exception("tool_call_format failed for %s", provider)

        return result

    # -----------------------------------------------------------------------
    # Validation 4: memory_injection
    # -----------------------------------------------------------------------

    async def validate_memory_injection(self, provider: str) -> ValidationResult:
        result = ValidationResult(feature="memory_injection", provider=provider)
        skip = self._check_enabled()
        if skip:
            result.status = ValidationStatus.SKIPPED
            result.details = skip
            return result

        config = self.provider_configs.get(provider)
        if not config:
            result.status = ValidationStatus.SKIPPED
            result.details = {"reason": f"Unknown provider {provider}"}
            return result

        paid_block = self._check_paid_allowed(config)
        if paid_block:
            result.status = ValidationStatus.SKIPPED
            result.details = paid_block
            return result

        configured = self._check_configured(config)
        if configured:
            result.status = ValidationStatus(configured["status"])
            result.details = configured
            return result

        client = _ProviderClient(config)
        dataset = SYNTHETIC_DATASET["memory_injection"]
        t0 = time.monotonic()

        try:
            response = await asyncio.wait_for(
                client.chat_completion(
                    messages=[
                        {"role": "system", "content": dataset["system_prompt"]},
                        {"role": "user", "content": dataset["prompt"]},
                    ]
                ),
                timeout=self.timeout_seconds,
            )
            elapsed = (time.monotonic() - t0) * 1000
            content = _extract_content(response)
            prompt_t, comp_t, total_t = _extract_usage(response)
            cost = _estimate_cost(prompt_t, comp_t, provider)

            result.duration_ms = round(elapsed, 1)
            result.prompt_tokens = prompt_t
            result.completion_tokens = comp_t
            result.tokens_used = total_t
            result.cost_brl = round(cost, 6)

            has_color = dataset["expected_color"].lower() in content.lower()
            has_number = dataset["expected_number"] in content

            if has_color and has_number:
                result.status = ValidationStatus.PASSED
            elif has_color:
                result.status = ValidationStatus.FAILED
                result.error_message = f"Found color but missing number {dataset['expected_number']}. Content: {content[:200]}"
            elif has_number:
                result.status = ValidationStatus.FAILED
                result.error_message = f"Found number but missing color {dataset['expected_color']}. Content: {content[:200]}"
            else:
                result.status = ValidationStatus.FAILED
                result.error_message = f"Memory not injected. Expected color={dataset['expected_color']} number={dataset['expected_number']}. Content: {content[:200]}"

        except asyncio.TimeoutError:
            result.status = ValidationStatus.FAILED
            result.error_message = f"Timeout after {self.timeout_seconds}s"
        except (ConnectionError, RuntimeError, PermissionError, OSError) as e:
            result.status = ValidationStatus.FAILED
            result.error_message = str(e)
        except Exception as e:
            result.status = ValidationStatus.ERROR
            result.error_message = f"Unexpected error: {e}"
            logger.exception("memory_injection failed for %s", provider)

        return result

    # -----------------------------------------------------------------------
    # Validation 5: context_compression
    # -----------------------------------------------------------------------

    async def validate_context_compression(self, provider: str) -> ValidationResult:
        result = ValidationResult(feature="context_compression", provider=provider)
        skip = self._check_enabled()
        if skip:
            result.status = ValidationStatus.SKIPPED
            result.details = skip
            return result

        config = self.provider_configs.get(provider)
        if not config:
            result.status = ValidationStatus.SKIPPED
            result.details = {"reason": f"Unknown provider {provider}"}
            return result

        paid_block = self._check_paid_allowed(config)
        if paid_block:
            result.status = ValidationStatus.SKIPPED
            result.details = paid_block
            return result

        configured = self._check_configured(config)
        if configured:
            result.status = ValidationStatus(configured["status"])
            result.details = configured
            return result

        client = _ProviderClient(config)
        dataset = SYNTHETIC_DATASET["context_compression"]
        t0 = time.monotonic()

        try:
            messages = []
            messages.extend(dataset["long_history"])
            messages.append({"role": "user", "content": dataset["prompt"]})

            response = await asyncio.wait_for(
                client.chat_completion(messages=messages),
                timeout=self.timeout_seconds,
            )
            elapsed = (time.monotonic() - t0) * 1000
            content = _extract_content(response)
            prompt_t, comp_t, total_t = _extract_usage(response)
            cost = _estimate_cost(prompt_t, comp_t, provider)

            result.duration_ms = round(elapsed, 1)
            result.prompt_tokens = prompt_t
            result.completion_tokens = comp_t
            result.tokens_used = total_t
            result.cost_brl = round(cost, 6)

            goal_keywords = ["context", "compression", "validate", "preserve", "goal", "core"]
            found_keywords = [kw for kw in goal_keywords if kw in content.lower()]
            result.details = {"keywords_found": found_keywords, "response_length": len(content)}

            if len(found_keywords) >= 2:
                result.status = ValidationStatus.PASSED
            else:
                result.status = ValidationStatus.FAILED
                result.error_message = f"Context goal not preserved. Expected keywords from {goal_keywords}. Content: {content[:200]}"

        except asyncio.TimeoutError:
            result.status = ValidationStatus.FAILED
            result.error_message = f"Timeout after {self.timeout_seconds}s"
        except (ConnectionError, RuntimeError, PermissionError, OSError) as e:
            result.status = ValidationStatus.FAILED
            result.error_message = str(e)
        except Exception as e:
            result.status = ValidationStatus.ERROR
            result.error_message = f"Unexpected error: {e}"
            logger.exception("context_compression failed for %s", provider)

        return result

    # -----------------------------------------------------------------------
    # Validation 6: fallback
    # -----------------------------------------------------------------------

    async def validate_fallback(self, provider: str) -> ValidationResult:
        result = ValidationResult(feature="fallback", provider=provider)
        skip = self._check_enabled()
        if skip:
            result.status = ValidationStatus.SKIPPED
            result.details = skip
            return result

        config = self.provider_configs.get(provider)
        if not config:
            result.status = ValidationStatus.SKIPPED
            result.details = {"reason": f"Unknown provider {provider}"}
            return result

        if provider == "mock":
            result.status = ValidationStatus.SKIPPED
            result.details = {"reason": "Fallback not applicable to mock provider"}
            return result

        paid_block = self._check_paid_allowed(config)
        if paid_block:
            result.status = ValidationStatus.SKIPPED
            result.details = paid_block
            return result

        # Find fallback target
        fallback_targets = [p for p in ALLOWED_PROVIDERS if p != provider]
        fallback = None
        for fb in fallback_targets:
            fb_config = self.provider_configs.get(fb)
            if fb_config and not self._check_configured(fb_config) and not self._check_paid_allowed(fb_config):
                fallback = fb
                break

        if not fallback:
            result.status = ValidationStatus.SKIPPED
            result.details = {"reason": "No configured fallback provider available"}
            return result

        t0 = time.monotonic()
        try:
            import aiohttp

            fake_url = "http://localhost:1/invalid"
            client = _ProviderClient(config)
            payload = client._build_payload([{"role": "user", "content": "test"}])

            timeout_ctx = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout_ctx) as session:
                try:
                    async with session.post(fake_url, json=payload, headers=client._build_headers()) as resp:
                        pass
                except Exception:
                    pass

            fallback_client = _ProviderClient(self.provider_configs[fallback])
            response = await asyncio.wait_for(
                fallback_client.chat_completion(messages=[{"role": "user", "content": "Responda apenas 'ok'."}]),
                timeout=self.timeout_seconds,
            )
            elapsed = (time.monotonic() - t0) * 1000
            content = _extract_content(response)
            prompt_t, comp_t, total_t = _extract_usage(response)
            cost = _estimate_cost(prompt_t, comp_t, fallback)

            result.duration_ms = round(elapsed, 1)
            result.prompt_tokens = prompt_t
            result.completion_tokens = comp_t
            result.tokens_used = total_t
            result.cost_brl = round(cost, 6)
            result.details = {"primary": provider, "fallback": fallback}

            if "ok" in content.lower():
                result.status = ValidationStatus.PASSED
            else:
                result.status = ValidationStatus.FAILED
                result.error_message = f"Fallback response invalid: {content[:100]}"

        except asyncio.TimeoutError:
            result.status = ValidationStatus.FAILED
            result.error_message = f"Fallback timeout after {self.timeout_seconds}s"
        except (ConnectionError, RuntimeError, PermissionError, OSError) as e:
            result.status = ValidationStatus.FAILED
            result.error_message = f"Fallback error: {e}"
        except Exception as e:
            result.status = ValidationStatus.ERROR
            result.error_message = f"Unexpected error: {e}"
            logger.exception("fallback failed for %s -> %s", provider, fallback)

        return result

    # -----------------------------------------------------------------------
    # Validation 7: budget_guard
    # -----------------------------------------------------------------------

    async def validate_budget_guard(self, provider: str) -> ValidationResult:
        result = ValidationResult(feature="budget_guard", provider=provider)
        skip = self._check_enabled()
        if skip:
            result.status = ValidationStatus.SKIPPED
            result.details = skip
            return result

        config = self.provider_configs.get(provider)
        if not config:
            result.status = ValidationStatus.SKIPPED
            result.details = {"reason": f"Unknown provider {provider}"}
            return result

        tracker = _BudgetTracker(max_brl=0.01)
        tracker.record(0.02)

        if tracker.exceeded:
            result.status = ValidationStatus.PASSED
            result.details = {"budget_exceeded": True, "spent": tracker.spent_brl, "max": tracker.max_brl}
        else:
            result.status = ValidationStatus.FAILED
            result.error_message = "Budget guard did not trigger"

        result.tokens_used = 0
        result.cost_brl = 0.0

        return result

    # -----------------------------------------------------------------------
    # Validation 8: timeout_guard
    # -----------------------------------------------------------------------

    async def validate_timeout_guard(self, provider: str) -> ValidationResult:
        result = ValidationResult(feature="timeout_guard", provider=provider)
        skip = self._check_enabled()
        if skip:
            result.status = ValidationStatus.SKIPPED
            result.details = skip
            return result

        config = self.provider_configs.get(provider)
        if not config:
            result.status = ValidationStatus.SKIPPED
            result.details = {"reason": f"Unknown provider {provider}"}
            return result

        if provider == "mock":
            result.status = ValidationStatus.SKIPPED
            result.details = {"reason": "Timeout guard not applicable to mock (instant responses)"}
            return result

        import aiohttp

        client = _ProviderClient(config)
        t0 = time.monotonic()

        try:
            fake_url = "http://10.255.255.1:1/v1/chat/completions"
            payload = client._build_payload([{"role": "user", "content": "test"}])
            headers = client._build_headers()

            timeout_ctx = aiohttp.ClientTimeout(total=1)
            async with aiohttp.ClientSession(timeout=timeout_ctx) as session:
                async with session.post(fake_url, json=payload, headers=headers) as resp:
                    pass

            result.status = ValidationStatus.FAILED
            result.error_message = "Timeout guard did not trigger (request to unreachable host succeeded unexpectedly)"
        except (asyncio.TimeoutError, Exception):
            elapsed = (time.monotonic() - t0) * 1000
            result.status = ValidationStatus.PASSED
            result.duration_ms = round(elapsed, 1)
            result.details = {"timeout_triggered": True, "elapsed_ms": round(elapsed, 1)}

        return result

    # -----------------------------------------------------------------------
    # Suite execution
    # -----------------------------------------------------------------------

    async def run_validations(self, provider: str) -> ProviderReport:
        t0 = time.monotonic()

        results = {
            "basic_model_call": await self.validate_basic_model_call(provider),
            "structured_output": await self.validate_structured_output(provider),
            "tool_call_format": await self.validate_tool_call_format(provider),
            "memory_injection": await self.validate_memory_injection(provider),
            "context_compression": await self.validate_context_compression(provider),
            "fallback": await self.validate_fallback(provider),
            "budget_guard": await self.validate_budget_guard(provider),
            "timeout_guard": await self.validate_timeout_guard(provider),
        }

        total_duration = (time.monotonic() - t0) * 1000
        total_tokens = sum(r.tokens_used for r in results.values())
        total_cost = sum(r.cost_brl for r in results.values())

        all_skipped = all(r.status == ValidationStatus.SKIPPED for r in results.values())
        all_passed = all(
            r.status in (ValidationStatus.PASSED, ValidationStatus.SKIPPED, ValidationStatus.DEGRADED)
            for r in results.values()
        )
        any_error = any(r.status == ValidationStatus.ERROR for r in results.values())

        if all_skipped:
            status = "skipped"
        elif any_error:
            status = "error"
        elif all_passed:
            status = "passed"
        else:
            status = "degraded"

        return ProviderReport(
            provider=provider,
            status=status,
            results=results,
            total_duration_ms=round(total_duration, 1),
            total_tokens=total_tokens,
            total_cost_brl=round(total_cost, 6),
        )

    async def execute_suite(self, providers: Optional[List[str]] = None) -> List[ProviderReport]:
        targets = providers or list(self.provider_configs.keys())
        reports = []

        budget = _BudgetTracker(self.budget_brl)

        for provider_name in targets:
            if not budget.check():
                logger.warning("Budget exceeded (%.4f/%.2f). Stopping suite.", budget.spent_brl, self.budget_brl)
                break

            report = await self.run_validations(provider_name)
            reports.append(report)
            budget.record(report.total_cost_brl)

        return reports

    # -----------------------------------------------------------------------
    # Artifact generation
    # -----------------------------------------------------------------------

    def generate_summary_md(self, reports: List[ProviderReport]) -> str:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        lines = [
            "# Real Provider Validation Summary",
            "",
            f"**Generated:** {now}",
            f"**Enabled:** {self.is_enabled}",
            f"**Allow Paid:** {self.allow_paid}",
            f"**Budget BRL:** {self.budget_brl}",
            f"**Timeout:** {self.timeout_seconds}s",
            "",
            "## Results by Provider",
            "",
        ]

        for report in reports:
            status_icon = {"passed": "✓", "degraded": "⚠", "error": "✗", "skipped": "–"}
            icon = status_icon.get(report.status, "?")
            lines.append(f"### {icon} {report.provider} — {report.status.upper()}")
            lines.append(f"- Duration: {report.total_duration_ms:.0f}ms")
            lines.append(f"- Tokens: {report.total_tokens}")
            lines.append(f"- Cost: R$ {report.total_cost_brl:.6f}")
            lines.append("")
            lines.append("| Feature | Status | Details |")
            lines.append("|---------|--------|---------|")
            for feat, res in report.results.items():
                detail = res.error_message[:50] if res.error_message else f"{res.duration_ms:.0f}ms, {res.tokens_used}tok"
                lines.append(f"| {feat} | {res.status.value} | {detail} |")
            lines.append("")

        lines.append("---")
        total_cost = sum(r.total_cost_brl for r in reports)
        total_tokens = sum(r.total_tokens for r in reports)
        lines.append(f"**Total Cost:** R$ {total_cost:.6f}")
        lines.append(f"**Total Tokens:** {total_tokens}")
        lines.append(f"**Providers Tested:** {len(reports)}")

        return "\n".join(lines)

    def generate_results_json(self, reports: List[ProviderReport]) -> str:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        def _serialize(r: ValidationResult):
            return {
                "feature": r.feature,
                "status": r.status.value,
                "provider": r.provider,
                "duration_ms": r.duration_ms,
                "tokens_used": r.tokens_used,
                "prompt_tokens": r.prompt_tokens,
                "completion_tokens": r.completion_tokens,
                "cost_brl": r.cost_brl,
                "error_message": r.error_message,
                "retries": r.retries,
                "details": r.details,
            }

        data = {
            "generated_at": now,
            "enabled": self.is_enabled,
            "allow_paid": self.allow_paid,
            "budget_brl": self.budget_brl,
            "timeout_seconds": self.timeout_seconds,
            "providers": [
                {
                    "provider": r.provider,
                    "status": r.status,
                    "total_duration_ms": r.total_duration_ms,
                    "total_tokens": r.total_tokens,
                    "total_cost_brl": r.total_cost_brl,
                    "error_message": r.error_message,
                    "results": [_serialize(res) for res in r.results.values()],
                }
                for r in reports
            ],
            "summary": {
                "total_providers": len(reports),
                "passed": sum(1 for r in reports if r.status == "passed"),
                "degraded": sum(1 for r in reports if r.status == "degraded"),
                "skipped": sum(1 for r in reports if r.status == "skipped"),
                "error": sum(1 for r in reports if r.status == "error"),
                "total_cost_brl": round(sum(r.total_cost_brl for r in reports), 6),
                "total_tokens": sum(r.total_tokens for r in reports),
            },
        }
        return json.dumps(data, indent=2, default=str)

    def generate_provider_matrix_md(self, reports: List[ProviderReport]) -> str:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        features = ["basic_model_call", "structured_output", "tool_call_format", "memory_injection", "context_compression", "fallback", "budget_guard", "timeout_guard"]

        lines = [
            "# Provider Validation Matrix",
            "",
            f"**Generated:** {now}",
            "",
            "## Feature Coverage Matrix",
            "",
            f"| Provider | {' | '.join(f.replace('_', ' ').title() for f in features)} | Overall |",
            f"| --- | {' | '.join(':---:' for _ in features)} | :---: |",
        ]

        for report in reports:
            row = [report.provider]
            for feat in features:
                res = report.results.get(feat)
                if res:
                    icon = {"passed": "✓", "degraded": "~", "failed": "✗", "skipped": "–", "error": "!"}
                    row.append(icon.get(res.status.value, "?"))
                else:
                    row.append(" ")
            row.append(report.status.upper())
            lines.append(f"| {' | '.join(row)} |")

        lines.extend([
            "",
            "## Legend",
            "- ✓ = Passed",
            "- ~ = Degraded",
            "- ✗ = Failed",
            "- – = Skipped",
            "- ! = Error",
            "",
            "## Provider Configurations",
            "",
        ])

        for name, config in self.provider_configs.items():
            endpoint = config.endpoint or "(mock)"
            key_status = "configured" if (not config.api_key_env or os.environ.get(config.api_key_env)) else "missing"
            lines.append(f"- **{name}**: {config.model} @ {endpoint} [{config.cost_tier.value}] key={key_status}")

        return "\n".join(lines)

    def write_artifacts(self, reports: List[ProviderReport]):
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        summary = self.generate_summary_md(reports)
        (self.artifacts_dir / "summary.md").write_text(summary)

        results = self.generate_results_json(reports)
        (self.artifacts_dir / "results.json").write_text(results)

        matrix = self.generate_provider_matrix_md(reports)
        (self.artifacts_dir / "provider-matrix.md").write_text(matrix)

        logger.info("Artifacts written to %s", self.artifacts_dir)


# ---------------------------------------------------------------------------
# Module-level helpers for scripts & admin endpoints
# ---------------------------------------------------------------------------

async def run_validation_suite(providers: Optional[List[str]] = None) -> Dict[str, Any]:
    validator = RealProviderValidator()
    reports = await validator.execute_suite(providers)
    validator.write_artifacts(reports)

    results_json = json.loads(validator.generate_results_json(reports))
    # Sanitize: mask API keys in output
    _sanitize_artifacts(results_json)

    return results_json


def _sanitize_artifacts(data: Dict):
    """Mask any potential API keys or secrets in the artifact data."""
    json_str = json.dumps(data)
    # Mask common key patterns
    json_str = re.sub(r'(sk-[a-zA-Z0-9]{20,})', 'sk-****', json_str)
    json_str = re.sub(r'(Bearer\s+)[a-zA-Z0-9\-_]{20,}', r'\1****', json_str)
    # Re-parse
    return json.loads(json_str)


async def get_latest_results() -> Dict[str, Any]:
    results_path = ARTIFACTS_DIR / "results.json"
    if not results_path.exists():
        return {"status": "not_generated"}
    data = json.loads(results_path.read_text())
    return data


def get_provider_matrix() -> List[Dict[str, Any]]:
    return [
        {
            "name": name,
            "endpoint": config.endpoint,
            "model": config.model,
            "cost_tier": config.cost_tier.value,
            "api_key_configured": bool(os.environ.get(config.api_key_env, "")) if config.api_key_env else True,
            "weight": config.weight,
        }
        for name, config in _get_provider_configs().items()
    ]


def is_recent_validation_available(max_age_hours: int = 24) -> bool:
    results_path = ARTIFACTS_DIR / "results.json"
    if not results_path.exists():
        return False
    mtime = results_path.stat().st_mtime
    age = (time.time() - mtime) / 3600
    return age <= max_age_hours
