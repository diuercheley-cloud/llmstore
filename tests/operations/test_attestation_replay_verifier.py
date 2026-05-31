import uuid

from app.services.operations.attestation_framework.attestation_service import SovereignExecutionAttestationService
from app.services.operations.attestation_framework.replay_verifier import AttestationReplayVerifier
from app.utils.crypto_signer import sign_payload


def test_replay_verifier_attestation_and_chain():
    service = SovereignExecutionAttestationService()
    verifier = AttestationReplayVerifier()
    attestation = service.issue_attestation(
        {
            "client_id": uuid.uuid4(),
            "subject_type": "sandbox_run",
            "subject_ref": "run-1",
            "attestation_scope": "sandbox",
            "payload": {"result": "ok"},
            "signature": sign_payload("sandbox"),
        },
        "sandbox_run",
    )
    chain = service.build_attestation_chain([attestation])
    replay = verifier.replay_attestation(attestation)
    replay_chain = verifier.replay_chain(chain)

    assert replay["match"] is True
    assert replay_chain["match"] is True
    assert verifier.compare_replay_hashes("a", "b")["match"] is False
