import uuid

import pytest
from app.services.operations.attestation_framework.attestation_service import (
    SovereignExecutionAttestationService,
)
from app.utils.crypto_signer import sign_payload


def test_issue_verify_revoke_and_chain():
    service = SovereignExecutionAttestationService()
    client_id = uuid.uuid4()
    first = service.issue_attestation(
        {
            "client_id": client_id,
            "subject_type": "workflow",
            "subject_ref": "wf-1",
            "attestation_scope": "operations",
            "payload": {"step": "prepare", "secret_token": "hidden"},
            "signature": sign_payload("workflow"),
        },
        "workflow",
    )
    second = service.issue_attestation(
        {
            "client_id": client_id,
            "subject_type": "workflow",
            "subject_ref": "wf-1",
            "attestation_scope": "operations",
            "payload": {"step": "execute"},
            "signature": sign_payload("workflow"),
            "previous_attestation_hash": first.attestation_hash,
            "attestation_chain_position": "2",
        },
        "workflow",
    )
    verification = service.verify_attestation(first)
    chain = service.build_attestation_chain([first, second])

    assert verification.verification_status == "passed"
    assert service.validate_chain_integrity(chain) is True
    assert "placeholder attestation only" in service.explain_attestation(first)

    revoked = service.revoke_attestation(second, "superseded")
    assert revoked.attestation_status == "revoked"


def test_revoke_requires_reason():
    service = SovereignExecutionAttestationService()
    attestation = service.issue_attestation(
        {
            "client_id": uuid.uuid4(),
            "subject_type": "execution",
            "subject_ref": "exec-1",
            "attestation_scope": "operations",
            "payload": {"x": 1},
            "signature": sign_payload("execution"),
        },
        "execution",
    )
    with pytest.raises(ValueError, match="reason is required"):
        service.revoke_attestation(attestation, "")
