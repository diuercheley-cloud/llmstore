import uuid

from app.services.operations.attestation_framework.attestation_service import (
    SovereignExecutionAttestationService,
)
from app.services.operations.attestation_framework.federation_bundle import (
    AttestationFederationBundleService,
)
from app.services.operations.attestation_framework.receipts import (
    build_attestation_receipt,
    build_bundle_receipt,
    build_chain_receipt,
    build_verification_receipt,
)
from app.utils.crypto_signer import sign_payload


def test_receipts_include_required_fields():
    service = SovereignExecutionAttestationService()
    bundle_service = AttestationFederationBundleService()
    attestation = service.issue_attestation(
        {
            "client_id": uuid.uuid4(),
            "subject_type": "workflow",
            "subject_ref": "wf-1",
            "attestation_scope": "operations",
            "payload": {"x": 1},
            "signature": sign_payload("workflow"),
        },
        "workflow",
    )
    verification = service.verify_attestation(attestation)
    chain = service.build_attestation_chain([attestation])
    bundle, _ = bundle_service.create_bundle([attestation], "airgap-b")

    for receipt in (
        build_attestation_receipt(attestation),
        build_verification_receipt(verification),
        build_chain_receipt(chain),
        build_bundle_receipt(bundle),
    ):
        assert receipt["receipt_type"]
        assert receipt["client_id"]
        assert receipt["subject_id"]
        assert receipt["immutable_hash"]
        assert receipt["payload_hash"]
        assert receipt["deterministic_version"] == "v1"
        assert len(receipt["signature"]) >= 64  # Hex signature length
