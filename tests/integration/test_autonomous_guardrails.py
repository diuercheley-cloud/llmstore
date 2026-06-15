import pytest
from app.api.dependencies import get_db
from app.models.commercial.commercial_attestation_runtime import CommercialRuntimeAttestation
from app.models.commercial.commercial_autonomous_guardrails import (
    CommercialAutonomousExecutionReceipt,
    CommercialHumanApprovalCheckpoint,
)
from app.models.commercial.commercial_governance import CommercialPolicyBundle
from app.models.commercial.commercial_runtime_fabric import CommercialRuntimeFabricHealth
from app.models.commercial.commercial_sovereign_governance import (
    CommercialHardwareAttestationRecord,
)
from app.services.governance.autonomous_guardrails import AutonomousGuardrailsService
from app.services.governance.blast_radius_analysis import sha256_hex
from sqlalchemy import desc, select


async def _seed_runtime_trust(session):
    session.add(
        CommercialRuntimeAttestation(
            node_id="node-1",
            cluster_id="cluster-a",
            tenant_id="tenant-a",
            runtime_hash=sha256_hex("runtime"),
            evidence_hash=sha256_hex("runtime-evidence"),
            immutable_hash=sha256_hex("runtime-immutable"),
            status="trusted",
            trusted=True,
            evidence_json={},
            measurement_json={},
            metadata_json={},
        )
    )
    session.add(
        CommercialHardwareAttestationRecord(
            node_id="node-1",
            cluster_id="cluster-a",
            attestation_type="tpm",
            status="trusted",
            evidence_json={},
            evidence_hash=sha256_hex("hardware-evidence"),
        )
    )
    session.add(
        CommercialRuntimeFabricHealth(
            node_id="node-1",
            status="healthy",
            metrics={},
            quarum_status=True,
            degraded_mode_active=False,
        )
    )
    session.add(
        CommercialPolicyBundle(
            bundle_name="guardrails-bundle",
            bundle_version="1.0.0",
            bundle_type="operational",
            mode="enforce",
            status="active",
            rules_json={"autonomous": "enabled"},
            immutable_hash=sha256_hex("bundle"),
        )
    )
    await session.commit()


@pytest.mark.asyncio
async def test_approval_execute_receipt_verify_flow(session):
    await _seed_runtime_trust(session)
    service = AutonomousGuardrailsService()
    await service.create_policy(
        session,
        policy_name="safe-throttle-policy",
        action_type="safe_throttle",
        tenant_id="tenant-a",
        require_human_approval=True,
        approval_stages_json=[{"stage": 1, "required_approvals": 1}],
        max_blast_radius_score=0.9,
    )

    request = {
        "action_type": "safe_throttle",
        "target_type": "runtime_node",
        "target_id": "node-1",
        "tenant_id": "tenant-a",
        "node_id": "node-1",
        "cluster_id": "cluster-a",
        "runtime_nodes": ["node-1"],
        "affected_tenants": ["tenant-a"],
    }
    first = await service.execute_guarded_action(session, request=request)
    assert first["status"] == "pending_approval"

    checkpoints = (
        (
            await session.execute(
                select(CommercialHumanApprovalCheckpoint).order_by(
                    CommercialHumanApprovalCheckpoint.created_at.asc()
                )
            )
        )
        .scalars()
        .all()
    )
    assert checkpoints
    for checkpoint in checkpoints:
        await service.checkpointing.approve_checkpoint(
            session, checkpoint_id=checkpoint.id, approver="approver-1"
        )

    second = await service.execute_guarded_action(session, request=request)
    assert second["status"] == "executed"

    receipt = (
        (
            await session.execute(
                select(CommercialAutonomousExecutionReceipt).order_by(
                    desc(CommercialAutonomousExecutionReceipt.created_at)
                )
            )
        )
        .scalars()
        .first()
    )
    verified = await service.verify_receipt(session, receipt.id)

    assert verified.verification_status == "verified"
    assert verified.receipt_hash


@pytest.mark.asyncio
async def test_guardrails_admin_endpoints(session, app_client_factory, admin_token_headers):
    from app.main import app

    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    client = await app_client_factory(app)
    try:
        response = await client.get("/admin/guardrails/status", headers=admin_token_headers)
        assert response.status_code == 200
        assert "autonomous_risk_matrix" in response.json()

        checkpoints = await client.get("/admin/guardrails/checkpoints", headers=admin_token_headers)
        assert checkpoints.status_code == 200
        assert isinstance(checkpoints.json(), list)

        blast_radius = await client.get(
            "/admin/guardrails/blast-radius", headers=admin_token_headers
        )
        assert blast_radius.status_code == 200
        assert "items" in blast_radius.json()

        violations = await client.get("/admin/guardrails/violations", headers=admin_token_headers)
        assert violations.status_code == 200
        assert isinstance(violations.json(), list)

        receipts = await client.get("/admin/guardrails/receipts", headers=admin_token_headers)
        assert receipts.status_code == 200
        assert isinstance(receipts.json(), list)
    finally:
        app.dependency_overrides.pop(get_db, None)
        await client.aclose()
