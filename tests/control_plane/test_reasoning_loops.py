import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.core.config import get_settings
from app.services.agents.agent_llm_provider import MockAgentLLMProvider
from app.services.agents.reasoning.context_compressor import ContextCompressor
from app.services.agents.reasoning.output_repair import OutputRepairService
from app.services.agents.reasoning.semantic_model_fallback import SemanticModelFallback
from app.services.agents.reasoning.structured_output import StructuredOutputValidator


def patch_settings(env_dict):
    patcher = patch.dict(os.environ, env_dict)
    patcher.start()
    get_settings.cache_clear()
    return patcher


@pytest.mark.asyncio
async def test_structured_output_validation():
    content = 'Here is the result: ```json\n{"status": "ok"}\n```'
    result = StructuredOutputValidator.parse_and_validate(content)
    assert result == {"status": "ok"}


@pytest.mark.asyncio
async def test_output_repair_success():
    llm = MockAgentLLMProvider()
    llm.generate = AsyncMock(return_value={"output": '{"status": "repaired"}'})

    repair_svc = OutputRepairService(llm)
    agent_def = MagicMock(instructions="test")
    run = MagicMock()

    result = await repair_svc.repair_output("bad json", "JSONDecodeError", agent_def, run)
    assert result == {"status": "repaired"}
    llm.generate.assert_called_once()


@pytest.mark.asyncio
async def test_context_compression_triggers():
    p = patch_settings({"AGENT_CONTEXT_COMPRESSION_ENABLED": "true"})
    try:
        compressor = ContextCompressor(max_tokens_threshold=10)
        history = [{"role": "system", "content": "S"}, {"role": "user", "content": "U" * 100}]

        compressed = await compressor.compress_if_needed(history)
        assert len(compressed) >= 2
        assert any("[CONTEXT SUMMARY]" in m["content"] for m in compressed)
    finally:
        p.stop()


@pytest.mark.asyncio
async def test_semantic_fallback_model_selection():
    p = patch_settings({"AGENT_SEMANTIC_MODEL_FALLBACK_ENABLED": "true"})
    try:
        fallback = SemanticModelFallback()

        model = await fallback.get_fallback_model("gpt-4o-mini", "json_malformed")
        assert model == "gpt-4o"

        model = await fallback.get_fallback_model("gpt-4o", "context_length_exceeded")
        assert model == "gpt-4o-32k"
    finally:
        p.stop()


@pytest.mark.asyncio
async def test_secret_redaction():
    compressor = ContextCompressor()
    content = "My api-key: sk-12345, secret=password123, token is XYZ"
    redacted = compressor.redact_secrets(content)
    assert "sk-12345" not in redacted
    assert "password123" not in redacted
    assert "XYZ" not in redacted
    assert "[REDACTED]" in redacted
