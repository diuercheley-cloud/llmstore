import uuid

from app.services.operations.attestation_framework.attestation_service import (
    SovereignExecutionAttestationService,
)
from app.services.operations.attestation_framework.federation_bundle import (
    AttestationFederationBundleService,
)
from app.services.operations.attestation_framework.replay_verifier import AttestationReplayVerifier
from app.utils.crypto_signer import sign_payload


def test_federation_bundle_create_export_import_verify():
    attestation_service = SovereignExecutionAttestationService()
    bundle_service = AttestationFederationBundleService()
    replay_verifier = AttestationReplayVerifier()

    attestation = attestation_service.issue_attestation(
        {
            "client_id": uuid.uuid4(),
            "subject_type": "adapter_registry",
            "subject_ref": "registry-entry-1",
            "attestation_scope": "operations",
            "payload": {"registry_hash": "abc"},
            "signature": sign_payload("registry"),
        },
        "adapter_registry",
    )
    bundle, payload = bundle_service.create_bundle([attestation], "target-airgap")
    exported = bundle_service.export_bundle(bundle)
    imported = bundle_service.import_bundle(payload)
    verification = bundle_service.verify_bundle(imported)
    replay = replay_verifier.replay_bundle(imported)

    assert exported["bundle_status"] == "exported"
    assert imported.bundle_status == "verified"
    assert verification["verification_status"] == "passed"
    assert replay["match"] is True
