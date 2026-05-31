from typing import Any

from app.models.operations.federation_sync import FederationTrustNegotiation
from app.services.operations.federation_sync.environment_registry import TRUST_SCORES
from app.services.operations.federation_sync.hash_utils import compute_negotiation_hash, sha256_hex


class FederationTrustNegotiationService:
    def negotiate(self, source_environment: Any, target_environment: Any) -> FederationTrustNegotiation:
        requirements = self.evaluate_trust_requirements(source_environment, target_environment)
        logical_payload = {
            "client_id": str(source_environment.client_id),
            "source_environment_id": source_environment.id,
            "target_environment_id": target_environment.id,
            "required_trust_level": requirements["required_trust_level"],
            "negotiated_trust_level": requirements["negotiated_trust_level"],
            "replay_verification_required": requirements["replay_verification_required"],
            "offline_verification_required": requirements["offline_verification_required"],
        }
        return FederationTrustNegotiation(
            id=sha256_hex({"kind": "federation_negotiation_id", **logical_payload}),
            client_id=source_environment.client_id,
            source_environment_id=source_environment.id,
            target_environment_id=target_environment.id,
            negotiation_status=requirements["negotiation_status"],
            required_trust_level=requirements["required_trust_level"],
            negotiated_trust_level=requirements["negotiated_trust_level"],
            replay_verification_required=requirements["replay_verification_required"],
            offline_verification_required=requirements["offline_verification_required"],
            immutable_hash=compute_negotiation_hash(logical_payload),
        )

    def validate_negotiation(self, negotiation: FederationTrustNegotiation) -> dict[str, Any]:
        accepted = negotiation.negotiation_status == "accepted"
        return {
            "valid": accepted and negotiation.offline_verification_required and negotiation.replay_verification_required,
            "accepted": accepted,
            "placeholder_trust_only": True,
            "signature_is_real_trust": False,
        }

    def evaluate_trust_requirements(self, source: Any, target: Any) -> dict[str, Any]:
        if "isolated" in {source.trust_level, target.trust_level}:
            return {
                "negotiation_status": "denied",
                "required_trust_level": "isolated",
                "negotiated_trust_level": "isolated",
                "replay_verification_required": True,
                "offline_verification_required": True,
            }
        level = source.trust_level if TRUST_SCORES[source.trust_level] <= TRUST_SCORES[target.trust_level] else target.trust_level
        if "verified" in {source.trust_level, target.trust_level}:
            level = "verified"
        return {
            "negotiation_status": "accepted",
            "required_trust_level": level,
            "negotiated_trust_level": level,
            "replay_verification_required": True,
            "offline_verification_required": True,
        }

    def explain_negotiation(self, negotiation: FederationTrustNegotiation) -> dict[str, Any]:
        return {
            "negotiation_id": negotiation.id,
            "negotiation_status": negotiation.negotiation_status,
            "required_trust_level": negotiation.required_trust_level,
            "negotiated_trust_level": negotiation.negotiated_trust_level,
            "rules": [
                "isolated cannot synchronize automatically",
                "restricted requires manual review for conflicts",
                "verified requires replay-verifiable bundles",
                "signature does not count as real trust",
            ],
        }
