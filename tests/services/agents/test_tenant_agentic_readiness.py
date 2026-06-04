import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

sys.path.append(os.path.join(os.path.dirname(__file__), "../../../control_plane"))

from app.core.config import get_settings
from app.services.agents.tenant_agentic_readiness import TenantAgenticReadinessService


@pytest.fixture
def service():
    db = AsyncMock()
    return TenantAgenticReadinessService(db)


def _setattr_many(settings, values):
    original = {key: getattr(settings, key) for key in values}
    for key, value in values.items():
        setattr(settings, key, value)
    return original


def _restore_many(settings, original):
    for key, value in original.items():
        setattr(settings, key, value)


@pytest.mark.asyncio
async def test_runtime_posture_blocks_mock_llm_in_production(service):
    settings = get_settings()
    original = _setattr_many(
        settings,
        {
            "deployment_mode": "production",
            "agent_llm_provider": "mock",
            "agent_allow_mock_llm_in_production": False,
            "agent_executor_mock_mode": False,
            "agent_executor_dry_run_mode": False,
            "agent_executor_allow_simulation": False,
            "agent_tool_sandbox_enabled": True,
        },
    )
    try:
        report = await service._check_runtime_posture("tenant-1")
        assert report["status"] == "blocked"
        assert "Mock LLM provider is active" in report["details"]["blockers"][0]
    finally:
        _restore_many(settings, original)


@pytest.mark.asyncio
async def test_integrations_posture_blocks_mock_memory_and_connector_in_production(service):
    settings = get_settings()
    original = _setattr_many(
        settings,
        {
            "deployment_mode": "production",
            "agent_memory_enabled": True,
            "agent_memory_vector_provider": "mock",
            "agent_memory_embeddings_provider": "mock",
            "agent_connector_catalog_enabled": True,
            "agent_connector_mode": "mock",
            "agent_connector_real_http_enabled": False,
            "agent_eval_provider": "mock",
            "agent_code_sandbox_provider": "mock",
        },
    )
    try:
        report = await service._check_integrations_posture("tenant-1")
        assert report["status"] == "blocked"
        blockers = " ".join(report["details"]["blockers"])
        assert "AGENT_MEMORY_VECTOR_PROVIDER=mock" in blockers
        assert "AGENT_CONNECTOR_MODE=mock" in blockers
        assert "AGENT_EVAL_PROVIDER=mock" in blockers
    finally:
        _restore_many(settings, original)


@pytest.mark.asyncio
async def test_operational_evidence_warns_when_artifacts_missing_in_appliance(service):
    settings = get_settings()
    original = _setattr_many(settings, {"deployment_mode": "appliance"})
    original_base_dir = service._base_dir
    try:
        service._base_dir = Path("/tmp/non-existent-agentic-evidence")
        report = await service._check_operational_evidence("tenant-1")
        assert report["status"] == "warning"
        assert "production_agentic_e2e" in report["details"]["missing"]
    finally:
        service._base_dir = original_base_dir
        _restore_many(settings, original)
