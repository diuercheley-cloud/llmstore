import pytest
import re
from app.utils.model_prompting import apply_prompt_template_settings


def is_spacing_broken(text: str) -> bool:
    if len(text) > 50 and text.count(" ") < len(text) / 20:
        return True
    glued_patterns = [
        r"Iaman",
        r"softwareengineering",
        r"helpwith",
        r"assistyou",
    ]
    for pattern in glued_patterns:
        if re.search(pattern, text):
            return True
    return False


def test_spacing_heuristic():
    assert is_spacing_broken("IamanAIassistantdesignedtohelpwithsoftwareengineeringtasks.") is True
    assert is_spacing_broken("I am an AI assistant designed to help with software engineering tasks.") is False


@pytest.mark.asyncio
async def test_bonsai_response_spacing_simulation():
    bad_response = "IamanAIassistantdesignedtohelpwithsoftwareengineeringtasks.Iamheretoassistyouwithyourcodingneeds.HowcanIhelpyoutoday?"
    assert is_spacing_broken(bad_response) is True

    good_response = "I am an AI assistant designed to help with software engineering tasks. I am here to assist you with your coding needs. How can I help you today?"
    assert is_spacing_broken(good_response) is False


def test_bonsai_chatml_template_has_double_newline_after_im_end():
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
    template = updated["chat_template"]
    assert "<|im_end|>" in template
    after_im_end = template.split("<|im_end|>")[1]
    assert after_im_end.startswith("' + '\\n' + '\\n'")


def test_gemma_repeat_penalty_applied():
    payload = {
        "model": "gemma",
        "messages": [
            {"role": "user", "content": "Hello"},
        ],
    }
    updated = apply_prompt_template_settings(
        payload,
        prompt_template="gemma",
        include_reasoning=False,
        backend="llama.cpp",
    )
    assert updated["repeat_penalty"] == 1.2


def test_non_llama_cpp_backend_skips_template():
    payload = {
        "model": "gemma",
        "messages": [{"role": "user", "content": "Hello"}],
    }
    updated = apply_prompt_template_settings(
        payload,
        prompt_template="gemma",
        include_reasoning=False,
        backend="ollama",
    )
    assert "repeat_penalty" not in updated
