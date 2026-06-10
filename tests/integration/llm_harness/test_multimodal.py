import os
import pytest
from unittest.mock import MagicMock, AsyncMock

from scripts.llm_harness.multimodal.content_blocks import (
    TextBlock,
    ImageBlock,
    AudioBlock,
    VideoBlock,
)
from scripts.llm_harness.multimodal.images import (
    validate_and_load_image,
    get_image_metadata,
)
from scripts.llm_harness.multimodal.adapters import adapt_content_blocks_for_provider
from scripts.llm_harness.sanitizer import Sanitizer
from scripts.llm_harness.providers import OpenAICompatibleProvider, StubProvider


def test_content_blocks_creation():
    tb = TextBlock(text="hello world")
    assert tb.type == "text"
    assert tb.text == "hello world"

    ib = ImageBlock(image_url={"url": "data:image/png;base64,123"})
    assert ib.type == "image_url"
    assert ib.image_url["url"] == "data:image/png;base64,123"

    ab = AudioBlock(audio_url={"url": "data:audio/mp3;base64,123"}, metadata={"mime_type": "audio/mp3"})
    assert ab.type == "audio_url"
    assert ab.metadata["mime_type"] == "audio/mp3"

    vb = VideoBlock(video_url={"url": "data:video/mp4;base64,123"}, metadata={"mime_type": "video/mp4"})
    assert vb.type == "video_url"
    assert vb.metadata["mime_type"] == "video/mp4"


def test_image_validation_inside_outside(tmp_path):
    ws_path = tmp_path / "workspace"
    ws_path.mkdir()

    # Create dummy image inside workspace
    img_inside = ws_path / "test.png"
    img_inside.write_bytes(b"dummy png content")

    # Image inside workspace should be accepted
    meta, b64 = validate_and_load_image(str(img_inside), str(ws_path))
    assert meta.filename == "test.png"
    assert meta.mime_type == "image/png"
    assert meta.size_bytes == 17
    assert len(b64) > 0

    # Image outside workspace should be blocked
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    img_outside = outside_dir / "test.png"
    img_outside.write_bytes(b"dummy png outside")

    with pytest.raises(PermissionError, match="outside the workspace repository"):
        validate_and_load_image(str(img_outside), str(ws_path))


def test_image_validation_invalid_extension(tmp_path):
    ws_path = tmp_path / "workspace"
    ws_path.mkdir()

    img_invalid = ws_path / "test.txt"
    img_invalid.write_bytes(b"some text")

    with pytest.raises(ValueError, match="Unsupported image extension"):
        validate_and_load_image(str(img_invalid), str(ws_path))


def test_image_validation_too_large(tmp_path):
    ws_path = tmp_path / "workspace"
    ws_path.mkdir()

    img_large = ws_path / "large.png"
    img_large.write_bytes(b"x" * 100)

    # Limit to 50 bytes, should fail
    with pytest.raises(ValueError, match="exceeds the maximum limit"):
        validate_and_load_image(str(img_large), str(ws_path), max_size_bytes=50)


def test_image_metadata_generation(tmp_path):
    img_file = tmp_path / "test.jpg"
    img_file.write_bytes(b"some jpg content")

    meta = get_image_metadata(str(img_file))
    assert meta.filename == "test.jpg"
    assert meta.mime_type == "image/jpeg"
    assert len(meta.sha256) == 64


def test_adapt_content_blocks_for_provider():
    blocks = [
        TextBlock(text="Task instructions"),
        ImageBlock(image_url={"url": "data:image/png;base64,xyz"}),
        AudioBlock(audio_url={"url": "data:audio/mp3;base64,123"}, metadata={"mime_type": "audio/mp3"}),
        VideoBlock(video_url={"url": "data:video/mp4;base64,123"}, metadata={"mime_type": "video/mp4"}),
    ]

    # Multimodal disabled -> should fail
    with pytest.raises(ValueError, match="does not support multimodal input"):
        adapt_content_blocks_for_provider(blocks, multimodal_enabled=False)

    # Multimodal enabled -> should succeed and map metadata-only audio/video without base64
    adapted = adapt_content_blocks_for_provider(blocks, multimodal_enabled=True)
    assert len(adapted) == 4
    assert adapted[0]["type"] == "text"
    assert adapted[0]["text"] == "Task instructions"
    assert adapted[1]["type"] == "image_url"
    assert adapted[1]["image_url"]["url"] == "data:image/png;base64,xyz"
    assert adapted[2]["type"] == "audio_url"
    assert "123" not in adapted[2]["audio_url"]["url"]  # Ensure no leaks
    assert adapted[3]["type"] == "video_url"
    assert "123" not in adapted[3]["video_url"]["url"]  # Ensure no leaks


def test_provider_multimodal_checks():
    # OpenAICompatibleProvider health/config mock
    config_multimodal_off = {
        "provider": "openai-compatible",
        "api_key_env": "MOCK_KEY",
        "multimodal": False,
    }
    config_multimodal_on = {
        "provider": "openai-compatible",
        "api_key_env": "MOCK_KEY",
        "multimodal": True,
    }

    # StubProvider
    stub_provider_off = StubProvider(config_multimodal_off)
    stub_provider_on = StubProvider(config_multimodal_on)

    msg = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Describe this"},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,123"}},
            ],
        }
    ]

    # Off -> should fail clearly
    with pytest.raises(ValueError, match="does not support multimodal input"):
        import asyncio
        asyncio.run(stub_provider_off.chat_completion(msg))

    # On -> should pass (StubProvider will execute successfully or mock response)
    res = asyncio.run(stub_provider_on.chat_completion(msg))
    assert res is not None


def test_sanitizer_redacts_base64():
    raw_report = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "See this image:"},
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64,iVBORw0KGgoAAAANS=="}},
                ],
            }
        ]
    }
    sanitized = Sanitizer.sanitize_data(raw_report)
    serialized = str(sanitized)
    assert "iVBORw0KG" not in serialized
    assert "[REDACTED_IMAGE_BASE64]" in serialized
