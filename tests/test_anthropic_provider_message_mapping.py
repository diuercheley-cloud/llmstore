"""Tests for Anthropic provider Messages API mapping — system prompt, role mapping, content blocks."""

import json
import sys
from pathlib import Path
from typing import Any

import pytest

from app.services.providers.anthropic_provider import AnthropicProvider

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def provider():
    return AnthropicProvider()


def test_extract_system_from_messages(provider):
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello"},
    ]
    remaining = list(messages)
    system = provider._extract_system(remaining)
    assert system == "You are a helpful assistant."
    assert len(remaining) == 1
    assert remaining[0]["role"] == "user"


def test_extract_system_multiple_parts(provider):
    messages = [
        {"role": "system", "content": "Part one."},
        {"role": "user", "content": "Hi"},
        {"role": "system", "content": "Part two."},
    ]
    remaining = list(messages)
    system = provider._extract_system(remaining)
    assert system == "Part one.\nPart two."
    assert len(remaining) == 1


def test_extract_system_none(provider):
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi"},
    ]
    remaining = list(messages)
    system = provider._extract_system(remaining)
    assert system is None
    assert len(remaining) == 2


def test_extract_system_with_content_blocks(provider):
    messages = [
        {"role": "system", "content": [{"type": "text", "text": "Block system."}]},
        {"role": "user", "content": "Ok"},
    ]
    remaining = list(messages)
    system = provider._extract_system(remaining)
    assert system == "Block system."
    assert len(remaining) == 1


def test_extract_system_empty_text(provider):
    messages = [
        {"role": "system", "content": ""},
        {"role": "user", "content": "Hi"},
    ]
    remaining = list(messages)
    system = provider._extract_system(remaining)
    assert system is None


def test_map_messages_removes_system(provider):
    messages = [
        {"role": "system", "content": "You are a bot."},
        {"role": "user", "content": "Hello"},
    ]
    mapped = provider._map_messages(messages)
    assert len(mapped) == 1
    assert mapped[0]["role"] == "user"
    assert mapped[0]["content"] == "Hello"


def test_map_messages_user_and_assistant(provider):
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there"},
        {"role": "user", "content": "How are you?"},
    ]
    mapped = provider._map_messages(messages)
    assert len(mapped) == 3
    assert mapped[0]["role"] == "user"
    assert mapped[1]["role"] == "assistant"
    assert mapped[2]["role"] == "user"


def test_map_content_string(provider):
    result = provider._map_content("Hello world")
    assert result == "Hello world"


def test_map_content_text_block(provider):
    result = provider._map_content([{"type": "text", "text": "Hello"}])
    assert result == [{"type": "text", "text": "Hello"}]


def test_map_content_image_block(provider):
    fake_data = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAA="
    url = f"data:image/png;base64,{fake_data}"
    result = provider._map_content([{"type": "image_url", "image_url": {"url": url}}])
    assert isinstance(result, list)
    assert result[0]["type"] == "image"
    assert result[0]["source"]["type"] == "base64"
    assert result[0]["source"]["media_type"] == "image/png"
    assert result[0]["source"]["data"] == fake_data


def test_to_openai_format_extracts_text(provider):
    raw = {
        "id": "msg_01abc123",
        "content": [
            {"type": "text", "text": "The answer is 42"},
        ],
        "usage": {"input_tokens": 10, "output_tokens": 5},
    }
    result = provider._to_openai_format(raw, "claude-3-haiku-20240307")
    assert result["choices"][0]["message"]["content"] == "The answer is 42"
    assert result["usage"]["prompt_tokens"] == 10
    assert result["usage"]["completion_tokens"] == 5
    assert result["usage"]["total_tokens"] == 15


def test_to_openai_format_multiple_blocks(provider):
    raw = {
        "id": "msg_02xyz",
        "content": [
            {"type": "tool_use", "name": "get_weather"},
            {"type": "text", "text": "Let me check the weather."},
        ],
        "usage": {"input_tokens": 20, "output_tokens": 15},
    }
    result = provider._to_openai_format(raw, "claude-3-sonnet")
    assert result["choices"][0]["message"]["content"] == "Let me check the weather."


def test_to_openai_format_no_text_block(provider):
    raw = {
        "id": "msg_03",
        "content": [
            {"type": "tool_use", "name": "get_weather"},
        ],
        "usage": {"input_tokens": 5, "output_tokens": 3},
    }
    result = provider._to_openai_format(raw, "claude-3-haiku")
    assert result["choices"][0]["message"]["content"] == ""


def test_to_openai_format_empty_content(provider):
    raw = {
        "id": "msg_04",
        "content": [],
        "usage": {"input_tokens": 0, "output_tokens": 0},
    }
    result = provider._to_openai_format(raw, "claude-3-haiku")
    assert result["choices"][0]["message"]["content"] == ""
    assert result["usage"]["total_tokens"] == 0


def test_messages_api_payload_shape(provider):
    messages = [
        {"role": "system", "content": "You are Claude."},
        {"role": "user", "content": "Say OK"},
    ]
    remaining = list(messages)
    system = provider._extract_system(remaining)
    mapped = provider._map_messages(messages)
    assert system == "You are Claude."
    assert len(mapped) == 1
    assert mapped[0]["role"] == "user"
