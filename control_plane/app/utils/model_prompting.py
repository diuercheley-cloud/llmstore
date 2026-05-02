from __future__ import annotations

import json
import re
from typing import Any

_THINK_BLOCK_RE = re.compile(
    r"<think>.*?</think>", re.DOTALL | re.IGNORECASE
)


def detect_architecture(
    *,
    model_id: str,
    model_file: str,
    model_alias: str | None = None,
    metadata_json: str | None = None,
) -> str | None:
    metadata = _parse_metadata(metadata_json)
    for key in ("architecture", "model_architecture", "arch"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().lower()

    joined = " ".join(
        filter(None, [model_id, model_file, model_alias or ""])
    ).lower()
    if "gemma" in joined:
        return "gemma"
    if "qwen3" in joined:
        return "qwen3"
    if "bonsai" in joined or "bonzai" in joined:
        return "qwen3"
    if "qwen" in joined:
        return "qwen"
    return None


def detect_prompt_template(
    *,
    model_id: str,
    model_file: str,
    model_alias: str | None = None,
    metadata_json: str | None = None,
) -> str | None:
    architecture = detect_architecture(
        model_id=model_id,
        model_file=model_file,
        model_alias=model_alias,
        metadata_json=metadata_json,
    )
    if architecture == "gemma":
        return "gemma"
    if architecture and architecture.startswith("qwen"):
        return "qwen"
    return None


def apply_prompt_template_settings(
    request_payload: dict[str, Any],
    *,
    prompt_template: str | None,
    include_reasoning: bool,
    backend: str,
    bonsai_template_fallback: str | None = None,
) -> dict[str, Any]:
    updated = dict(request_payload)
    if backend != "llama.cpp":
        return updated
    if prompt_template == "qwen":
        template = bonsai_template_fallback or "chatml"
        if template == "chatml":
            template = (
                "{% for message in messages %}"
                "{{'<|im_start|>' + message['role'] + '\\n'"
                " + message['content'] + '<|im_end|>'"
                " + '\\n' + '\\n'}}"
                "{% endfor %}"
                "{% if add_generation_prompt %}"
                "{{ '<|im_start|>assistant\\n' }}"
                "{% endif %}"
            )
        updated["chat_template"] = template
        if not include_reasoning:
            updated["reasoning_format"] = "none"
            template_kwargs = dict(
                updated.get("chat_template_kwargs") or {}
            )
            template_kwargs["enable_thinking"] = False
            updated["chat_template_kwargs"] = template_kwargs
    elif prompt_template == "gemma":
        updated["repeat_penalty"] = 1.2
        if not include_reasoning:
            updated["reasoning_format"] = "none"
            template_kwargs = dict(updated.get("chat_template_kwargs") or {})
            template_kwargs["enable_thinking"] = False
            updated["chat_template_kwargs"] = template_kwargs
    return updated


def sanitize_assistant_text(
    content: str | None,
    *,
    prompt_template: str | None,
    include_reasoning: bool,
) -> str | None:
    if content is None or include_reasoning:
        return content
    if prompt_template == "qwen":
        sanitized = _THINK_BLOCK_RE.sub("", content)
        sanitized = sanitized.replace("<think>", "").replace(
            "</think>", ""
        )
        return sanitized.strip()
    return content


def _parse_metadata(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}
