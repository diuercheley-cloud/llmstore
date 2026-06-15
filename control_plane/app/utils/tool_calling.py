import hashlib
import json
import logging
import re
from typing import Any

from app.core.config import get_settings
from fastapi import HTTPException

logger = logging.getLogger(__name__)
settings = get_settings()

TOOL_NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
DISALLOWED_SCHEMA_KEYS = {
    "$ref",
    "$defs",
    "definitions",
    "allOf",
    "oneOf",
    "not",
    "if",
    "then",
    "else",
    "dependentSchemas",
    "patternProperties",
    "unevaluatedProperties",
    "contentEncoding",
    "contentMediaType",
}
OPENROUTER_TOOL_PARAMETERS = {"tools", "tool_choice", "parallel_tool_calls"}


def provider_tool_capability(provider: str | None) -> str:
    normalized = (provider or "").strip().lower()
    if normalized in {
        "openai_compatible",
        "openrouter",
        "openai",
        "deepseek",
        "anthropic",
        "gemini",
        "bedrock",
        "mistral",
        "groq",
        "together",
    }:
        return "supported"
    if normalized in {"ollama", "vllm", "llama.cpp"}:
        return "unsupported"
    return "unsupported"


def provider_supports_native_tools(provider: str | None) -> bool:
    return provider_tool_capability(provider) == "supported"


def model_supports_native_tools(
    provider: str | None,
    metadata_json: str | dict[str, Any] | None = None,
) -> bool:
    normalized = (provider or "").strip().lower()
    if not provider_supports_native_tools(normalized):
        return False
    if normalized != "openrouter":
        return True

    metadata = _coerce_metadata(metadata_json)
    supported_parameters = metadata.get("supported_parameters")
    if isinstance(supported_parameters, list):
        normalized_parameters = {
            str(item).strip() for item in supported_parameters if str(item).strip()
        }
        # For OpenRouter, 'tools' is the minimum required to support native tool calling
        return "tools" in normalized_parameters

    capabilities = metadata.get("capabilities")
    if isinstance(capabilities, dict) and "tools" in capabilities:
        return bool(capabilities.get("tools"))

    # If OpenRouter and no metadata, we are permissive about 'tools' existence
    # but filter_unsupported_tooling_parameters will clean up 'tool_choice' and 'parallel_tool_calls'
    return True


def filter_unsupported_tooling_parameters(
    provider: str | None,
    payload: dict[str, Any],
    metadata_json: str | dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = (provider or "").strip().lower()
    if normalized != "openrouter":
        return payload

    metadata = _coerce_metadata(metadata_json)
    supported_parameters = metadata.get("supported_parameters")

    updated = dict(payload)
    removed = []

    if isinstance(supported_parameters, list):
        supported_set = {str(item).strip() for item in supported_parameters if str(item).strip()}
        # We only filter parameters that are in OPENROUTER_TOOL_PARAMETERS
        for param in OPENROUTER_TOOL_PARAMETERS:
            if param in updated and param not in supported_set:
                del updated[param]
                removed.append(param)
    else:
        # Fallback: If supported_parameters is missing for OpenRouter,
        # we are extremely conservative and remove tool_choice/parallel_tool_calls
        # because they are the most likely to cause 404 routing errors.
        for param in ["tool_choice", "parallel_tool_calls"]:
            if param in updated:
                del updated[param]
                removed.append(param)

    if removed:
        logger.warning(
            f"Removed unsupported or risky OpenRouter tooling parameters from request: {', '.join(removed)}"
        )

    return updated


def tooling_requested(
    *,
    tools: list[Any] | None,
    tool_choice: str | dict[str, Any] | None,
) -> bool:
    if tools:
        return True
    if tool_choice is None:
        return False
    if isinstance(tool_choice, str):
        return tool_choice == "required"
    return True


def sanitize_inert_tooling_fields(
    *,
    tools: list[Any] | None,
    tool_choice: str | dict[str, Any] | None,
    parallel_tool_calls: bool | None,
) -> tuple[list[Any] | None, str | dict[str, Any] | None, bool | None]:
    if tools:
        return tools, tool_choice, parallel_tool_calls
    return None, None, None


def validate_tooling_request(
    *,
    tools: list[Any] | None,
    tool_choice: str | dict[str, Any] | None,
    parallel_tool_calls: bool | None,
    response_format: dict[str, Any] | None,
) -> None:
    _ = parallel_tool_calls
    if tools:
        validate_tool_definitions(tools)
    validate_tool_choice(tool_choice=tool_choice, tools=tools or [])
    validate_response_format(response_format)


def validate_tool_definitions(tools: list[Any]) -> None:
    if len(tools) > settings.max_tools_per_request:
        raise HTTPException(
            status_code=400,
            detail={
                "message": f"too many tools: max {settings.max_tools_per_request} allowed per request",
                "code": "tools_too_many",
            },
        )

    for idx, tool in enumerate(tools):
        if not isinstance(tool, dict):
            raise _tool_request_error(
                "invalid_tool_definition", f"tool at index {idx} must be an object"
            )
        if tool.get("type") != "function":
            raise _tool_request_error(
                "invalid_tool_type", f"tool at index {idx} must have type=function"
            )

        function = tool.get("function")
        if not isinstance(function, dict):
            raise _tool_request_error(
                "invalid_tool_definition", f"tool at index {idx} must include function object"
            )

        name = function.get("name")
        if not isinstance(name, str) or not TOOL_NAME_RE.match(name):
            raise _tool_request_error(
                "invalid_tool_name",
                f"tool at index {idx} has invalid function name; use 1-64 chars [A-Za-z0-9_-]",
            )

        parameters = function.get("parameters")
        if parameters is not None:
            validate_tool_schema(parameters, tool_name=name)


def validate_tool_choice(
    *, tool_choice: str | dict[str, Any] | None, tools: list[dict[str, Any]]
) -> None:
    if tool_choice is None:
        return
    if isinstance(tool_choice, str):
        if tool_choice not in {"none", "auto", "required"}:
            raise _tool_request_error(
                "invalid_tool_choice",
                "tool_choice must be one of none, auto, required, or function object",
            )
        return
    if not isinstance(tool_choice, dict):
        raise _tool_request_error("invalid_tool_choice", "tool_choice must be a string or object")
    if tool_choice.get("type") != "function":
        raise _tool_request_error(
            "invalid_tool_choice", "tool_choice object must have type=function"
        )
    function = tool_choice.get("function")
    if not isinstance(function, dict) or not isinstance(function.get("name"), str):
        raise _tool_request_error("invalid_tool_choice", "tool_choice.function.name is required")
    name = function["name"]
    if not TOOL_NAME_RE.match(name):
        raise _tool_request_error("invalid_tool_choice", "tool_choice.function.name is invalid")
    tool_names = {item.get("function", {}).get("name") for item in tools if isinstance(item, dict)}
    if tools and name not in tool_names:
        raise _tool_request_error(
            "invalid_tool_choice", f"tool_choice references unknown tool '{name}'"
        )


def validate_response_format(response_format: dict[str, Any] | None) -> None:
    if response_format is None:
        return
    if not isinstance(response_format, dict):
        raise _tool_request_error("invalid_response_format", "response_format must be an object")


def validate_tool_schema(schema: Any, *, tool_name: str) -> None:
    if not isinstance(schema, dict):
        raise _tool_request_error(
            "invalid_tool_schema", f"tool '{tool_name}' parameters must be an object schema"
        )
    serialized = _safe_json_dumps(schema)
    if len(serialized.encode("utf-8")) > settings.max_tool_schema_bytes:
        raise _tool_request_error(
            "tool_schema_too_large",
            f"tool '{tool_name}' schema exceeds {settings.max_tool_schema_bytes} bytes",
        )
    _validate_schema_shape(schema, tool_name=tool_name)

    stats = _schema_stats(schema)
    if stats["max_depth"] > settings.max_tool_schema_depth:
        raise _tool_request_error(
            "tool_schema_too_deep",
            f"tool '{tool_name}' schema exceeds max depth {settings.max_tool_schema_depth}",
        )
    if stats["property_count"] > settings.max_tool_schema_properties:
        raise _tool_request_error(
            "tool_schema_too_large",
            f"tool '{tool_name}' schema exceeds max property count {settings.max_tool_schema_properties}",
        )


def _coerce_metadata(raw: str | dict[str, Any] | None) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str) or not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def extract_tool_calls_from_chat_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    tool_calls: list[dict[str, Any]] = []
    for choice in payload.get("choices", []) or []:
        message = choice.get("message") or {}
        for tool_call in message.get("tool_calls") or []:
            if isinstance(tool_call, dict):
                tool_calls.append(tool_call)
    return tool_calls


def sanitize_tool_calls(tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [sanitize_tool_call(item) for item in tool_calls]


def sanitize_tool_call(tool_call: dict[str, Any]) -> dict[str, Any]:
    function = tool_call.get("function") or {}
    raw_arguments = function.get("arguments")
    serialized_arguments = _serialize_arguments(raw_arguments)
    preview = _redacted_arguments_preview(raw_arguments)
    return {
        "id": tool_call.get("id"),
        "type": tool_call.get("type", "function"),
        "function": {
            "name": function.get("name"),
            "arguments_preview": preview,
            "arguments_size": len(serialized_arguments.encode("utf-8")),
            "arguments_truncated": len(serialized_arguments) > settings.tool_argument_preview_chars,
        },
    }


def enforce_tool_argument_limits(tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sanitized = sanitize_tool_calls(tool_calls)
    for item in sanitized:
        function = item.get("function") or {}
        if int(function.get("arguments_size") or 0) > settings.max_tool_arguments_bytes:
            name = function.get("name") or "unknown"
            raise HTTPException(
                status_code=502,
                detail={
                    "message": f"provider returned tool arguments exceeding {settings.max_tool_arguments_bytes} bytes for '{name}'",
                    "code": "tool_arguments_too_large",
                },
            )
    return sanitized


def chat_response_has_tool_calls(payload: dict[str, Any]) -> bool:
    return bool(extract_tool_calls_from_chat_payload(payload))


def _schema_stats(schema: Any, *, depth: int = 1) -> dict[str, int]:
    property_count = 0
    max_depth = depth
    if isinstance(schema, dict):
        for key in schema:
            if key in DISALLOWED_SCHEMA_KEYS:
                raise _tool_request_error(
                    "tool_schema_not_allowed", f"schema keyword '{key}' is not allowed"
                )

        properties = schema.get("properties")
        if isinstance(properties, dict):
            property_count += len(properties)
            for child_schema in properties.values():
                child = _schema_stats(child_schema, depth=depth + 1)
                property_count += child["property_count"]
                max_depth = max(max_depth, child["max_depth"])

        items = schema.get("items")
        if isinstance(items, dict):
            child = _schema_stats(items, depth=depth + 1)
            property_count += child["property_count"]
            max_depth = max(max_depth, child["max_depth"])
        elif isinstance(items, list):
            for child_schema in items:
                child = _schema_stats(child_schema, depth=depth + 1)
                property_count += child["property_count"]
                max_depth = max(max_depth, child["max_depth"])

        for key, value in schema.items():
            if key in {"properties", "items"}:
                continue
            child = _schema_stats(value, depth=depth)
            property_count += child["property_count"]
            max_depth = max(max_depth, child["max_depth"])
    elif isinstance(schema, list):
        for value in schema:
            child = _schema_stats(value, depth=depth)
            property_count += child["property_count"]
            max_depth = max(max_depth, child["max_depth"])
    return {"property_count": property_count, "max_depth": max_depth}


def _validate_schema_shape(schema: dict[str, Any], *, tool_name: str) -> None:
    schema_type = schema.get("type")
    if schema_type is not None and schema_type not in {
        "object",
        "array",
        "string",
        "number",
        "integer",
        "boolean",
        "null",
    }:
        raise _tool_request_error(
            "invalid_tool_schema", f"tool '{tool_name}' has unsupported schema type '{schema_type}'"
        )

    properties = schema.get("properties")
    if properties is not None and not isinstance(properties, dict):
        raise _tool_request_error(
            "invalid_tool_schema", f"tool '{tool_name}' properties must be an object"
        )

    required = schema.get("required")
    if required is not None:
        if not isinstance(required, list) or not all(isinstance(item, str) for item in required):
            raise _tool_request_error(
                "invalid_tool_schema", f"tool '{tool_name}' required must be a list of strings"
            )

    items = schema.get("items")
    if items is not None and not isinstance(items, (dict, list)):
        raise _tool_request_error(
            "invalid_tool_schema", f"tool '{tool_name}' items must be an object or list"
        )


def _serialize_arguments(arguments: Any) -> str:
    if isinstance(arguments, str):
        return arguments
    return _safe_json_dumps(arguments)


def _redacted_arguments_preview(arguments: Any) -> str:
    parsed = arguments
    if isinstance(arguments, str):
        try:
            parsed = json.loads(arguments)
        except Exception:
            digest = hashlib.sha256(arguments.encode("utf-8")).hexdigest()[:12]
            return f"[redacted-string len={len(arguments)} sha256={digest}]"
    if isinstance(parsed, dict):
        keys = sorted(str(key) for key in parsed.keys())
        return _truncate_preview(json.dumps({"shape": "object", "keys": keys}, ensure_ascii=True))
    if isinstance(parsed, list):
        return _truncate_preview(
            json.dumps({"shape": "array", "items": len(parsed)}, ensure_ascii=True)
        )
    return _truncate_preview(json.dumps({"shape": type(parsed).__name__}, ensure_ascii=True))


def _truncate_preview(value: str) -> str:
    return value[: settings.tool_argument_preview_chars]


def _safe_json_dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


def _tool_request_error(code: str, message: str) -> HTTPException:
    return HTTPException(status_code=400, detail={"message": message, "code": code})
