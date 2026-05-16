"""Lightweight contract for the trust domain."""


class TrustDomainContract:
    """Defines the stable contract surface for trust modularization."""

    allowed_inputs = (
        "attestation evidence",
        "cryptographic receipts",
        "integrity measurements",
        "replay verification requests",
        "trust graph snapshots",
    )
    emitted_events = (
        "trust.attestation.verified",
        "trust.receipt.issued",
        "trust.integrity.violation_detected",
        "trust.replay.validated",
        "trust.snapshot.recorded",
    )
    forbidden_dependencies = (
        "app.domains.financial",
        "app.domains.operations",
        "app.domains.sovereign",
    )
    deterministic_requirements = (
        "must validate evidence locally when offline",
        "must keep cryptographic verification paths deterministic",
        "must not require direct imports from other domain contracts",
        "must avoid mutable cross-domain state as a contract requirement",
    )

