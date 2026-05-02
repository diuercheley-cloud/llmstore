import pytest
from app.utils.model_prompting import (
    apply_prompt_template_settings,
    detect_architecture,
    detect_prompt_template,
)


def test_apply_prompt_template_settings_bonsai_fallback():
    payload = {
        "model": "bonsai",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello"},
        ],
    }

    updated = apply_prompt_template_settings(
        payload,
        prompt_template="qwen",
        include_reasoning=False,
        backend="llama.cpp",
        bonsai_template_fallback="chatml",
    )

    assert "chat_template" in updated
    assert updated["reasoning_format"] == "none"


def test_detect_architecture_bonsai():
    arch = detect_architecture(model_id="bonsai/bonsai-8B-GGUF", model_file="bonsai-8B.gguf")
    assert arch == "qwen3"

    template = detect_prompt_template(model_id="bonsai/bonsai-8B-GGUF", model_file="bonsai-8B.gguf")
    assert template == "qwen"


def test_detect_architecture_gemma():
    arch = detect_architecture(model_id="unsloth/gemma-4-E4B-it-GGUF", model_file="gemma-4-E4B-it-Q4_K_M.gguf")
    assert arch == "gemma"

    template = detect_prompt_template(model_id="unsloth/gemma-4-E4B-it-GGUF", model_file="gemma-4-E4B-it-Q4_K_M.gguf")
    assert template == "gemma"


def test_detect_architecture_gemma_alias():
    arch = detect_architecture(model_id="some-model", model_file="model.gguf", model_alias="gemma")
    assert arch == "gemma"


def test_gemma_template_sets_repeat_penalty():
    payload = {
        "model": "gemma",
        "messages": [{"role": "user", "content": "Hello"}],
    }
    updated = apply_prompt_template_settings(
        payload,
        prompt_template="gemma",
        include_reasoning=False,
        backend="llama.cpp",
    )
    assert updated.get("repeat_penalty") == 1.2
