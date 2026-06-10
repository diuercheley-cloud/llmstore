import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.agents.agent_bundle_signing import AgentBundleSigningService
from app.services.agents.agent_incident_playbooks import AgentIncidentPlaybookService
from app.services.agents.agent_scheduler import AgentScheduler
from app.services.agents.agent_usage_meter import AgentUsageMeter
from app.services.agents.marketplace_governance import MarketplaceGovernanceService, SubmissionStatus
from app.services.agents.memory_context_builder import MemoryContextBuilder
from app.services.agents.tool_adapter_contract import ToolAdapterContract
from app.services.agents.tool_audit import sanitize_payload


class ExampleAdapter(ToolAdapterContract):
    name = "example"
    version = "1.0.0"
    input_schema = {"type": "object"}
    output_schema = {"type": "object"}
    side_effect_level = "none"

    async def execute(self, **kwargs):
        return kwargs

    async def dry_run(self, **kwargs):
        return kwargs

    async def rollback(self, invocation_id: str, **kwargs):
        return {"invocation_id": invocation_id}

    async def healthcheck(self):
        return True


def test_agent_tool_audit_contract_and_bundle_signing():
    assert sanitize_payload({"api_key": "secret", "nested": ["sk-value"]}) == {
        "api_key": "[REDACTED]",
        "nested": ["[REDACTED]"],
    }
    assert ExampleAdapter().to_registry_dict()["rollback_supported"] is True

    signature = AgentBundleSigningService().sign_bundle(uuid.uuid4(), b"bundle", "key-1", "admin")
    assert signature.signature_value.startswith("sig:")


@pytest.mark.asyncio
async def test_agent_scheduler_disabled_and_incident_playbooks(monkeypatch):
    scheduler = AgentScheduler()
    scheduler.settings.agent_execution_plane_enabled = False
    await scheduler.start()
    assert scheduler.is_running is False

    playbooks = await AgentIncidentPlaybookService(MagicMock()).list_available_playbooks()
    assert playbooks
    assert all(playbook["destructive"] for playbook in playbooks)


@pytest.mark.asyncio
async def test_agent_usage_meter_existing_usage_is_idempotent():
    existing = object()
    result = MagicMock()
    result.scalar_one_or_none.return_value = existing
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)

    usage = await AgentUsageMeter(db).record_run_usage(
        "tenant", uuid.uuid4(), uuid.uuid4(), 10, 0.1
    )

    assert usage is existing
    db.add.assert_not_called()


def test_memory_context_builder_respects_budget():
    builder = MemoryContextBuilder(MagicMock())
    memories = [
        SimpleNamespace(item=SimpleNamespace(id=uuid.uuid4(), raw_content="abcd", summary="one")),
        SimpleNamespace(item=SimpleNamespace(id=uuid.uuid4(), raw_content="x" * 100, summary="large")),
    ]

    result = builder._build_block(memories, max_tokens=5)

    assert len(result["memory_ids"]) == 1
    assert "Relevant Memory" in result["context_block"]


@pytest.mark.asyncio
async def test_marketplace_governance_requires_approval_before_publish():
    service = MarketplaceGovernanceService(MagicMock())
    submission = await service.create_submission("agent", "1.0.0", "owner")

    with pytest.raises(ValueError, match="Must be 'approved'"):
        await service.publish_submission(submission.id)

    await service.approve_submission(submission.id, "reviewer")
    published = await service.publish_submission(submission.id)
    assert published.status == SubmissionStatus.PUBLISHED
