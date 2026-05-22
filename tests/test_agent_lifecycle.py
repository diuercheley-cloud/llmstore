import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agents import AgentRegistryEntry, AgentVersion, AgentLifecycleEvent, AgentPromotion, AgentDeprecation
from app.services.agents import agent_registry as reg_service
from app.services.agents import agent_lifecycle as lifecycle_service

@pytest.mark.asyncio
async def test_agent_registry_destructive_tool_default_approval(admin_client: AsyncClient, admin_token_headers):
    # 1. Create agent with a destructive tool (e.g. "delete")
    payload = {
        "name": "Destructive File Agent",
        "semantic_version": "0.1.0",
        "owner": "dev-team",
        "business_purpose": "Allows clearing workspace folders",
        "supported_surface_status": "internal",
        "risk_level": "medium",
        "allowed_tools": ["read_file", "delete"],
        "eval_baseline": "Validated on dummy dataset"
    }

    resp = await admin_client.post("/admin/agent-registry", json=payload, headers=admin_token_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Destructive File Agent"
    assert data["human_approval_required"] is True  # Destructive tool triggers default human approval
    entry_id = data["id"]

    # 2. Verify version records exist
    resp_versions = await admin_client.get(f"/admin/agent-registry/{entry_id}/versions", headers=admin_token_headers)
    assert resp_versions.status_code == 200
    versions = resp_versions.json()
    assert len(versions) == 1
    assert versions[0]["semantic_version"] == "0.1.0"


@pytest.mark.asyncio
async def test_agent_registry_instructions_change_bumps_version(admin_client: AsyncClient, admin_token_headers):
    # 1. Create a normal agent
    payload = {
        "name": "Version Test Agent",
        "semantic_version": "1.0.0",
        "owner": "qa-team",
        "instructions": "Be helpful.",
        "eval_baseline": "Initial pass"
    }
    resp = await admin_client.post("/admin/agent-registry", json=payload, headers=admin_token_headers)
    assert resp.status_code == 201
    entry_id = resp.json()["id"]

    # 2. Update instructions -> Bumps patch version automatically
    patch_payload = {
        "instructions": "Be extremely helpful and polite."
    }
    resp = await admin_client.patch(f"/admin/agent-registry/{entry_id}", json=patch_payload, headers=admin_token_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["semantic_version"] == "1.0.1"  # Automatically bumped from 1.0.0 -> 1.0.1
    assert data["instructions"] == "Be extremely helpful and polite."

    # Verify we have two versions now
    resp_versions = await admin_client.get(f"/admin/agent-registry/{entry_id}/versions", headers=admin_token_headers)
    assert resp_versions.status_code == 200
    versions = resp_versions.json()
    assert len(versions) == 2
    assert versions[0]["semantic_version"] == "1.0.1"
    assert versions[1]["semantic_version"] == "1.0.0"


@pytest.mark.asyncio
async def test_experimental_cannot_turn_supported(admin_client: AsyncClient, admin_token_headers):
    # 1. Create an experimental agent
    payload = {
        "name": "Experimental Agent",
        "semantic_version": "0.1.0",
        "supported_surface_status": "experimental",
    }
    resp = await admin_client.post("/admin/agent-registry", json=payload, headers=admin_token_headers)
    assert resp.status_code == 201
    entry_id = resp.json()["id"]

    # 2. Try to change surface status to supported -> fails with exception
    patch_payload = {
        "supported_surface_status": "supported"
    }
    resp = await admin_client.patch(f"/admin/agent-registry/{entry_id}", json=patch_payload, headers=admin_token_headers)
    assert resp.status_code == 400
    assert "Experimental agents cannot be promoted to supported" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_high_risk_requires_approval_gate(admin_client: AsyncClient, admin_token_headers, session: AsyncSession):
    # 1. Create a high-risk agent in draft
    payload = {
        "name": "High Risk Registry Agent",
        "semantic_version": "1.0.0",
        "owner": "sec-team",
        "risk_level": "high",
        "eval_baseline": "SecOps test baseline"
    }
    resp = await admin_client.post("/admin/agent-registry", json=payload, headers=admin_token_headers)
    assert resp.status_code == 201
    entry_id = resp.json()["id"]

    # 2. Submit for review (draft -> review)
    resp = await admin_client.post(f"/admin/agent-registry/{entry_id}/submit-review", headers=admin_token_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "review"

    # 3. Approve without approved_by -> fails
    approval_payload = {
        "approved_by": "",
        "metadata": {"test": True}
    }
    resp = await admin_client.post(f"/admin/agent-registry/{entry_id}/approve", json=approval_payload, headers=admin_token_headers)
    assert resp.status_code == 400
    assert "Approval signature" in resp.json()["detail"]

    # 4. Approve with approved_by -> succeeds
    approval_payload["approved_by"] = "Chief Risk Officer"
    resp = await admin_client.post(f"/admin/agent-registry/{entry_id}/approve", json=approval_payload, headers=admin_token_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"

    # Verify promotion entry exists in database
    result = await session.execute(
        select(AgentPromotion).where(AgentPromotion.agent_registry_id == uuid.UUID(entry_id))
    )
    promotion = result.scalars().first()
    assert promotion is not None
    assert promotion.approved_by == "Chief Risk Officer"


@pytest.mark.asyncio
async def test_activation_owner_and_baseline_gates(admin_client: AsyncClient, admin_token_headers, session: AsyncSession):
    # 1. Create agent without owner & baseline
    payload = {
        "name": "Gated Agent",
        "semantic_version": "0.1.0",
    }
    resp = await admin_client.post("/admin/agent-registry", json=payload, headers=admin_token_headers)
    assert resp.status_code == 201
    entry_id = resp.json()["id"]

    # Submit for review
    await admin_client.post(f"/admin/agent-registry/{entry_id}/submit-review", headers=admin_token_headers)
    # Approve (low risk level does not strictly require signature but CRO signs off anyway)
    await admin_client.post(
        f"/admin/agent-registry/{entry_id}/approve",
        json={"approved_by": "Compliance Lead"},
        headers=admin_token_headers
    )

    # 2. Try to activate -> fails because Owner is missing
    resp = await admin_client.post(f"/admin/agent-registry/{entry_id}/activate", headers=admin_token_headers)
    assert resp.status_code == 400
    assert "Owner is missing" in resp.json()["detail"]

    # Add owner but leave baseline missing
    await admin_client.patch(
        f"/admin/agent-registry/{entry_id}",
        json={"owner": "platform-ops"},
        headers=admin_token_headers
    )

    # Try to activate -> fails because eval baseline is missing
    resp = await admin_client.post(f"/admin/agent-registry/{entry_id}/activate", headers=admin_token_headers)
    assert resp.status_code == 400
    assert "Evaluation baseline is missing" in resp.json()["detail"]

    # Set eval baseline
    await admin_client.patch(
        f"/admin/agent-registry/{entry_id}",
        json={"eval_baseline": "Validated on production traffic shadow dataset"},
        headers=admin_token_headers
    )

    # Now activate -> succeeds!
    resp = await admin_client.post(f"/admin/agent-registry/{entry_id}/activate", headers=admin_token_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"


@pytest.mark.asyncio
async def test_governance_lifecycle_events_logged(admin_client: AsyncClient, admin_token_headers, session: AsyncSession):
    # 1. Create draft
    payload = {
        "name": "Audit Trail Agent",
        "owner": "audit-team",
        "eval_baseline": "Complies with ISO 27001",
        "risk_level": "medium"
    }
    resp = await admin_client.post("/admin/agent-registry", json=payload, headers=admin_token_headers)
    entry_id = resp.json()["id"]

    # 2. Transition draft -> review -> approved -> active -> paused -> active -> deprecated -> archived
    await admin_client.post(f"/admin/agent-registry/{entry_id}/submit-review", headers=admin_token_headers)
    await admin_client.post(
        f"/admin/agent-registry/{entry_id}/approve",
        json={"approved_by": "Auditor General"},
        headers=admin_token_headers
    )
    await admin_client.post(f"/admin/agent-registry/{entry_id}/activate", headers=admin_token_headers)
    await admin_client.post(f"/admin/agent-registry/{entry_id}/pause", headers=admin_token_headers)
    await admin_client.post(f"/admin/agent-registry/{entry_id}/activate", headers=admin_token_headers)
    await admin_client.post(
        f"/admin/agent-registry/{entry_id}/deprecate",
        json={"reason": "Replaced by newer version"},
        headers=admin_token_headers
    )
    await admin_client.post(f"/admin/agent-registry/{entry_id}/archive", headers=admin_token_headers)

    # 3. Retrieve all lifecycle events from DB and assert transition audit log correctness
    result = await session.execute(
        select(AgentLifecycleEvent)
        .where(AgentLifecycleEvent.agent_registry_id == uuid.UUID(entry_id))
        .order_by(AgentLifecycleEvent.created_at.asc())
    )
    events = result.scalars().all()

    # Events sequence:
    # 1. draft (create_draft)
    # 2. submit_review
    # 3. approve
    # 4. activate
    # 5. pause
    # 6. activate
    # 7. deprecate
    # 8. archive
    assert len(events) == 8
    
    assert events[0].event_type == "create_draft"
    assert events[0].to_status == "draft"

    assert events[1].event_type == "submit_review"
    assert events[1].from_status == "draft"
    assert events[1].to_status == "review"

    assert events[2].event_type == "approve"
    assert events[2].from_status == "review"
    assert events[2].to_status == "approved"

    assert events[3].event_type == "activate"
    assert events[3].from_status == "approved"
    assert events[3].to_status == "active"

    assert events[4].event_type == "pause"
    assert events[4].from_status == "active"
    assert events[4].to_status == "paused"

    assert events[5].event_type == "activate"
    assert events[5].from_status == "paused"
    assert events[5].to_status == "active"

    assert events[6].event_type == "deprecate"
    assert events[6].from_status == "active"
    assert events[6].to_status == "deprecated"

    assert events[7].event_type == "archive"
    assert events[7].from_status == "deprecated"
    assert events[7].to_status == "archived"
