"""Trust-related advisory invariants."""

from __future__ import annotations

from typing import Any

from app.services.invariants.base import InvariantResult, _as_mapping, advisory_result


def validate_confidential_mode_no_plaintext(payload: dict[str, Any] | None) -> InvariantResult:
    """Confidential-mode outputs must not expose plaintext content."""

    data = _as_mapping(payload)
    confidential_mode = bool(data.get("confidential_mode"))
    plaintext_fields = tuple(data.get("plaintext_fields") or ())
    plaintext_payload = data.get("plaintext_payload")
    has_plaintext = bool(plaintext_fields) or plaintext_payload not in (None, "", b"")
    passed = (not confidential_mode) or (not has_plaintext)
    return advisory_result(
        name="confidential_mode_no_plaintext",
        passed=passed,
        message="confidential mode must not expose plaintext",
        details={
            "confidential_mode": confidential_mode,
            "plaintext_field_count": len(plaintext_fields),
            "plaintext_payload_present": plaintext_payload not in (None, "", b""),
        },
    )


def validate_signed_artifact_has_signature_metadata(artifact: dict[str, Any] | None) -> InvariantResult:
    """Signed artifacts must carry metadata placeholder even before hard enforcement."""

    payload = _as_mapping(artifact)
    signed = bool(payload.get("signed"))
    metadata = _as_mapping(payload.get("signature_metadata"))
    has_placeholder = bool(metadata.get("placeholder")) or bool(metadata.get("algorithm"))
    passed = (not signed) or has_placeholder
    return advisory_result(
        name="signed_artifact_has_signature_metadata",
        passed=passed,
        message="signed artifact must include signature metadata",
        details={
            "signed": signed,
            "signature_metadata_present": bool(metadata),
            "placeholder_present": bool(metadata.get("placeholder")),
        },
    )
