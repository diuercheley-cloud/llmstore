from typing import Any

from app.models.operations.federation_sync import TRUST_LEVELS, SovereignFederationEnvironment
from app.services.operations.federation_sync.hash_utils import compute_negotiation_hash, sha256_hex

TRUST_SCORES = {
    "restricted": 1,
    "trusted": 2,
    "verified": 3,
    "isolated": 0,
}


class SovereignFederationEnvironmentRegistry:
    def register_environment(self, environment: dict[str, Any]) -> SovereignFederationEnvironment:
        logical_payload = {
            "client_id": str(environment["client_id"]),
            "environment_name": environment["environment_name"],
            "environment_type": environment["environment_type"],
            "federation_scope": environment["federation_scope"],
            "trust_level": environment.get("trust_level", "restricted"),
            "offline_only": environment.get("offline_only", True),
            "deterministic_version": environment.get("deterministic_version", "v1"),
        }
        environment_hash = sha256_hex({"kind": "environment", **logical_payload})
        immutable_hash = compute_negotiation_hash(
            {"kind": "environment_immutable", **logical_payload}
        )
        return SovereignFederationEnvironment(
            id=sha256_hex({"kind": "environment_id", **logical_payload}),
            client_id=environment["client_id"],
            environment_name=environment["environment_name"],
            environment_type=environment["environment_type"],
            federation_scope=environment["federation_scope"],
            trust_level=logical_payload["trust_level"],
            offline_only=logical_payload["offline_only"],
            deterministic_version=logical_payload["deterministic_version"],
            environment_hash=environment_hash,
            immutable_hash=immutable_hash,
        )

    def verify_environment(self, environment: SovereignFederationEnvironment) -> dict[str, Any]:
        trust_report = self.evaluate_environment_trust(environment)
        return {
            "valid": environment.offline_only and trust_report["trust_level"] in TRUST_LEVELS,
            "offline_only": environment.offline_only,
            "trust_level": environment.trust_level,
            "environment_hash": environment.environment_hash,
            "placeholder_trust_only": True,
        }

    def evaluate_environment_trust(
        self, environment: SovereignFederationEnvironment
    ) -> dict[str, Any]:
        return {
            "trust_level": environment.trust_level,
            "trust_score": TRUST_SCORES.get(environment.trust_level, 0),
            "offline_only": environment.offline_only,
            "hardware_backed": False,
            "external_trust": False,
        }

    def explain_environment(self, environment: SovereignFederationEnvironment) -> dict[str, Any]:
        verification = self.verify_environment(environment)
        return {
            "environment_id": environment.id,
            "environment_name": environment.environment_name,
            "environment_type": environment.environment_type,
            "federation_scope": environment.federation_scope,
            "verification": verification,
            "notes": [
                "offline federation only",
                "placeholder trust only",
                "no real hardware-backed federation trust",
            ],
        }
