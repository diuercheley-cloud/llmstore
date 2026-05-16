import uuid

from app.models.operations.attestation_framework import AttestationTrustPolicy
from app.services.operations.attestation_framework.attestation_service import SovereignExecutionAttestationService
from app.services.operations.attestation_framework.trust_policy_engine import AttestationTrustPolicyEngine


def test_trust_policy_engine_blocks_invalid_attestation_type():
    service = SovereignExecutionAttestationService()
    engine = AttestationTrustPolicyEngine()
    attestation = service.issue_attestation(
        {
            "client_id": uuid.uuid4(),
            "subject_type": "workflow",
            "subject_ref": "wf-1",
            "attestation_scope": "operations",
            "payload": {"x": 1},
            "signature_placeholder": "placeholder-signature:workflow",
        },
        "workflow",
    )
    policy = AttestationTrustPolicy(
        id="policy",
        client_id=attestation.client_id,
        policy_name="strict",
        allowed_attestation_types_json={"allowed": ["execution"]},
        immutable_hash="x" * 64,
    )
    result = engine.evaluate_attestation(attestation, policy)
    assert result["allowed"] is False
    assert "attestation_type_not_allowed" in result["reasons"]
