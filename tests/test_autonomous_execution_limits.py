import pytest

from app.models.commercial_attestation_runtime import CommercialRuntimeAttestation
from app.models.commercial_autonomous_guardrails import CommercialAutonomousExecutionPolicy
from app.models.commercial_governance import CommercialPolicyBundle
from app.models.commercial_runtime_fabric import CommercialRuntimeFabricHealth
from app.models.commercial_sovereign_governance import CommercialHardwareAttestationRecord
from app.services.governance.autonomous_execution_limits import AutonomousExecutionLimitsService
from app.services.governance.blast_radius_analysis import BlastRadiusAnalysisService, sha256_hex


async def _seed_enforcement_state(session, *, action_type: str, runtime_freeze: bool = False, rollback_allowed: bool = False):
    bundle = CommercialPolicyBundle(
        bundle_name="guardrails-bundle",
        bundle_version="1.0.0",
        bundle_type="operational",
        mode="enforce",
        status="active",
        rules_json={"autonomous": "enabled"},
        immutable_hash=sha256_hex("bundle"),
    )
    session.add(bundle)
    await session.flush()

    policy = CommercialAutonomousExecutionPolicy(
        policy_name=f"policy-{action_type}",
        action_type=action_type,
        tenant_id="tenant-a",
        policy_bundle_id=bundle.id,
        mode="guarded_enforce",
        max_blast_radius_score=0.95,
        require_human_approval=False,
        approval_stages_json=[{"stage": 1, "required_approvals": 1}],
        runtime_freeze_enabled=runtime_freeze,
        sovereign_hard_stop=True,
        rollback_allowed=rollback_allowed,
        is_active=True,
    )
    session.add(policy)
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
    await session.commit()
    return policy


@pytest.mark.asyncio
async def test_runtime_freeze_blocks_execution(session):
    await _seed_enforcement_state(session, action_type="safe_throttle", runtime_freeze=True)
    service = AutonomousExecutionLimitsService()
    blast_radius = await BlastRadiusAnalysisService().analyze_and_record(
        session,
        request={"action_type": "safe_throttle", "target_type": "runtime_node", "target_id": "node-1", "tenant_id": "tenant-a", "node_id": "node-1", "cluster_id": "cluster-a"},
    )

    result = await service.evaluate(
        session,
        request={"action_type": "safe_throttle", "target_type": "runtime_node", "target_id": "node-1", "tenant_id": "tenant-a", "node_id": "node-1", "cluster_id": "cluster-a"},
        blast_radius=blast_radius,
    )

    assert result["blocked"] is True
    assert "runtime_freeze_mode" in result["reasons"]


@pytest.mark.asyncio
async def test_sovereign_and_rollback_guards_block_unsafe_actions(session):
    await _seed_enforcement_state(session, action_type="rollback", rollback_allowed=False)
    service = AutonomousExecutionLimitsService()
    blast_radius = await BlastRadiusAnalysisService().analyze_and_record(
        session,
        request={
            "action_type": "rollback",
            "target_type": "runtime_node",
            "target_id": "node-1",
            "tenant_id": "tenant-a",
            "node_id": "node-1",
            "cluster_id": "cluster-a",
            "sovereign_scope": True,
            "rollback_requested": True,
        },
    )

    result = await service.evaluate(
        session,
        request={
            "action_type": "rollback",
            "target_type": "runtime_node",
            "target_id": "node-1",
            "tenant_id": "tenant-a",
            "node_id": "node-1",
            "cluster_id": "cluster-a",
            "sovereign_scope": True,
            "rollback_requested": True,
        },
        blast_radius=blast_radius,
    )

    assert result["blocked"] is True
    assert "sovereign_hard_stop" in result["reasons"]
    assert "unsafe_rollback" in result["reasons"]


@pytest.mark.asyncio
async def test_destructive_replay_is_automatically_blocked(session):
    await _seed_enforcement_state(session, action_type="destructive_replay")
    service = AutonomousExecutionLimitsService()
    blast_radius = await BlastRadiusAnalysisService().analyze_and_record(
        session,
        request={
            "action_type": "destructive_replay",
            "target_type": "workflow_execution",
            "target_id": "wf-1",
            "tenant_id": "tenant-a",
            "node_id": "node-1",
            "cluster_id": "cluster-a",
            "destructive": True,
        },
    )

    result = await service.evaluate(
        session,
        request={
            "action_type": "destructive_replay",
            "target_type": "workflow_execution",
            "target_id": "wf-1",
            "tenant_id": "tenant-a",
            "node_id": "node-1",
            "cluster_id": "cluster-a",
            "destructive": True,
        },
        blast_radius=blast_radius,
    )

    assert result["blocked"] is True
    assert "destructive_replay_blocked" in result["reasons"]
