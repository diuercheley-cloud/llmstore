from typing import Any

from app.models.operations.attestation_framework import (
    AttestationFederationBundle,
    AttestationTrustPolicy,
    SovereignExecutionAttestation,
)


class AttestationTrustPolicyEngine:
    def evaluate_attestation(self, attestation: SovereignExecutionAttestation, policy: AttestationTrustPolicy) -> dict[str, Any]:
        allowed_types = policy.allowed_attestation_types_json.get("allowed", [])
        reasons: list[str] = []
        if attestation.attestation_type not in allowed_types:
            reasons.append("attestation_type_not_allowed")
        if policy.require_signature and not attestation.signature:
            reasons.append("signature_missing")
        if policy.require_replay_verification and not attestation.replay_verifiable:
            reasons.append("replay_verification_missing")
        if policy.require_offline_verification and not attestation.offline_verifiable:
            reasons.append("offline_verification_missing")
        if policy.require_chain_integrity and not attestation.attestation_chain_position:
            reasons.append("chain_integrity_missing")
        return {"allowed": not reasons, "reasons": reasons, "subject": attestation.id}

    def evaluate_bundle(self, bundle: AttestationFederationBundle, policy: AttestationTrustPolicy) -> dict[str, Any]:
        reasons: list[str] = []
        if not policy.federation_allowed:
            reasons.append("federation_not_allowed")
        if policy.require_replay_verification and not bundle.replay_verifiable:
            reasons.append("replay_verification_missing")
        if policy.require_offline_verification and not bundle.offline_verifiable:
            reasons.append("offline_verification_missing")
        return {"allowed": not reasons, "reasons": reasons, "subject": bundle.id}

    def evaluate_chain(self, chain: list[Any], policy: AttestationTrustPolicy) -> dict[str, Any]:
        reasons: list[str] = []
        if policy.require_chain_integrity and not chain:
            reasons.append("chain_integrity_invalid")
        if policy.require_replay_verification and any(not item.replay_verifiable for item in chain):
            reasons.append("replay_verification_missing")
        return {"allowed": not reasons, "reasons": reasons, "subject": "chain"}

    def explain_policy_result(self, result: dict[str, Any]) -> str:
        if result["allowed"]:
            return "trust policy passed"
        return "trust policy blocked: " + ", ".join(result["reasons"])
