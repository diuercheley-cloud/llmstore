from typing import Any

from app.models.operations.attestation_framework import (
    AttestationChainLink,
    AttestationVerificationResult,
    SovereignExecutionAttestation,
)
from app.utils.crypto_signer import sign_payload
from app.services.operations.attestation_framework.hash_utils import (
    compute_attestation_hash,
    compute_chain_link_hash,
    sha256_hex,
)


def _sanitize_subject(subject: dict[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in subject.items():
        lowered = key.lower()
        if any(marker in lowered for marker in ("secret", "token", "password", "credential", "key")):
            redacted[key] = "redacted"
            continue
        if isinstance(value, dict):
            redacted[key] = _sanitize_subject(value)
        elif isinstance(value, list):
            redacted[key] = [_sanitize_subject(item) if isinstance(item, dict) else item for item in value]
        else:
            redacted[key] = value
    return redacted


class SovereignExecutionAttestationService:
    deterministic_version = "v1"

    def issue_attestation(self, subject: dict[str, Any], attestation_type: str) -> SovereignExecutionAttestation:
        signature = subject.get("signature") or sign_payload(f"{attestation_type}")
        if not signature:
            raise ValueError("signature is required")
        if not subject.get("replay_verifiable", True):
            raise ValueError("replay_verifiable is required")
        if not subject.get("offline_verifiable", True):
            raise ValueError("offline_verifiable is required")

        sanitized = _sanitize_subject(subject)
        payload_hash = sha256_hex(
            {
                "subject_type": sanitized["subject_type"],
                "subject_ref": sanitized["subject_ref"],
                "attestation_scope": sanitized.get("attestation_scope", sanitized["subject_type"]),
                "payload": sanitized.get("payload", sanitized),
                "deterministic_version": self.deterministic_version,
            }
        )
        chain_position = str(subject.get("attestation_chain_position", "1"))
        previous_hash = subject.get("previous_attestation_hash")
        attestation_hash = compute_attestation_hash(
            {
                "client_id": str(sanitized["client_id"]),
                "attestation_type": attestation_type,
                "subject_type": sanitized["subject_type"],
                "subject_ref": sanitized["subject_ref"],
                "attestation_scope": sanitized.get("attestation_scope", sanitized["subject_type"]),
                "payload_hash": payload_hash,
                "previous_attestation_hash": previous_hash,
                "signature": signature,
                "attestation_chain_position": chain_position,
                "replay_verifiable": True,
                "offline_verifiable": True,
                "deterministic_version": self.deterministic_version,
            }
        )
        immutable_hash = sha256_hex(
            {
                "kind": "sovereign_execution_attestation",
                "attestation_hash": attestation_hash,
                "attestation_status": "issued",
            }
        )
        return SovereignExecutionAttestation(
            id=sha256_hex({"kind": "attestation_id", "attestation_hash": attestation_hash}),
            client_id=sanitized["client_id"],
            attestation_type=attestation_type,
            subject_type=sanitized["subject_type"],
            subject_ref=sanitized["subject_ref"],
            attestation_scope=sanitized.get("attestation_scope", sanitized["subject_type"]),
            attestation_status="issued",
            deterministic_version=self.deterministic_version,
            payload_hash=payload_hash,
            attestation_hash=attestation_hash,
            previous_attestation_hash=previous_hash,
            signature=signature,
            attestation_chain_position=chain_position,
            replay_verifiable=True,
            offline_verifiable=True,
            immutable_hash=immutable_hash,
        )

    def verify_attestation(self, attestation: SovereignExecutionAttestation) -> AttestationVerificationResult:
        expected_hash = compute_attestation_hash(
            {
                "client_id": str(attestation.client_id),
                "attestation_type": attestation.attestation_type,
                "subject_type": attestation.subject_type,
                "subject_ref": attestation.subject_ref,
                "attestation_scope": attestation.attestation_scope,
                "payload_hash": attestation.payload_hash,
                "previous_attestation_hash": attestation.previous_attestation_hash,
                "signature": attestation.signature,
                "attestation_chain_position": attestation.attestation_chain_position,
                "replay_verifiable": attestation.replay_verifiable,
                "offline_verifiable": attestation.offline_verifiable,
                "deterministic_version": attestation.deterministic_version,
            }
        )
        replay_verified = expected_hash == attestation.attestation_hash
        offline_verified = bool(attestation.offline_verifiable and attestation.signature)
        chain_verified = bool(attestation.attestation_chain_position)
        passed = replay_verified and offline_verified and chain_verified
        status = "passed" if passed else "failed"
        summary = self.explain_attestation(attestation)
        return AttestationVerificationResult(
            id=sha256_hex({"kind": "verification_id", "attestation_id": attestation.id, "status": status}),
            client_id=attestation.client_id,
            attestation_id=attestation.id,
            verification_type="attestation",
            verification_status=status,
            verification_summary=summary,
            replay_verified=replay_verified,
            chain_verified=chain_verified,
            offline_verified=offline_verified,
            immutable_hash=sha256_hex({"kind": "verification", "attestation_hash": attestation.attestation_hash, "status": status}),
        )

    def revoke_attestation(self, attestation: SovereignExecutionAttestation, reason: str) -> SovereignExecutionAttestation:
        if not reason or not reason.strip():
            raise ValueError("reason is required")
        attestation.attestation_status = "revoked"
        attestation.immutable_hash = sha256_hex(
            {
                "kind": "sovereign_execution_attestation",
                "attestation_hash": attestation.attestation_hash,
                "attestation_status": "revoked",
                "reason": reason.strip(),
            }
        )
        return attestation

    def build_attestation_chain(self, attestations: list[SovereignExecutionAttestation]) -> list[AttestationChainLink]:
        ordered = sorted(attestations, key=lambda item: int(item.attestation_chain_position))
        chain: list[AttestationChainLink] = []
        previous_link_hash: str | None = None
        for attestation in ordered:
            current_link_hash = compute_chain_link_hash(
                {
                    "client_id": str(attestation.client_id),
                    "attestation_id": attestation.id,
                    "attestation_hash": attestation.attestation_hash,
                    "previous_link_hash": previous_link_hash,
                    "chain_position": attestation.attestation_chain_position,
                    "replay_verifiable": attestation.replay_verifiable,
                }
            )
            chain.append(
                AttestationChainLink(
                    id=sha256_hex({"kind": "chain_link_id", "link_hash": current_link_hash}),
                    client_id=attestation.client_id,
                    attestation_id=attestation.id,
                    previous_link_hash=previous_link_hash,
                    current_link_hash=current_link_hash,
                    chain_position=attestation.attestation_chain_position,
                    replay_verifiable=attestation.replay_verifiable,
                    immutable_hash=sha256_hex({"kind": "chain_link", "link_hash": current_link_hash}),
                )
            )
            previous_link_hash = current_link_hash
        return chain

    def validate_chain_integrity(self, chain: list[AttestationChainLink]) -> bool:
        previous_link_hash: str | None = None
        for link in sorted(chain, key=lambda item: int(item.chain_position)):
            if link.previous_link_hash != previous_link_hash:
                return False
            previous_link_hash = link.current_link_hash
        return True

    def explain_attestation(self, attestation: SovereignExecutionAttestation) -> str:
        return (
            f"placeholder attestation only; type={attestation.attestation_type}; "
            f"subject={attestation.subject_type}:{attestation.subject_ref}; "
            f"offline_verifiable={attestation.offline_verifiable}; "
            f"replay_verifiable={attestation.replay_verifiable}; "
            f"hardware_backed_trust=false"
        )
