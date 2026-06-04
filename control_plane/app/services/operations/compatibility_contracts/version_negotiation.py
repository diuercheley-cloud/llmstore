from typing import Any

from app.services.operations.compatibility_contracts.compatibility_matrix import (
    CompatibilityMatrixService,
)
from app.services.operations.compatibility_contracts.semantic_versioning import (
    SemanticVersioningService,
)


class VersionNegotiationService:
    def __init__(self) -> None:
        self.semver = SemanticVersioningService()
        self.matrix_service = CompatibilityMatrixService()

    def negotiate(self, source_version: str, target_version: str) -> dict[str, Any]:
        matrix = self.matrix_service.build_matrix(source_version, target_version)
        evaluation = self.matrix_service.evaluate_compatibility(matrix)
        comparison = self.semver.compare_versions(source_version, target_version)
        if evaluation["blocked"]:
            negotiated_version = None
            negotiation_status = "conflicted"
        else:
            negotiated_version = source_version if comparison["order"] <= 0 else target_version
            negotiation_status = "accepted"
        return {
            "source_version": source_version,
            "target_version": target_version,
            "negotiated_version": negotiated_version,
            "negotiation_status": negotiation_status,
            "replay_verifiable": matrix["replay_safe"],
            "matrix": matrix,
        }

    def validate_negotiated_version(self, session: Any) -> bool:
        source = self._get(session, "source_version")
        target = self._get(session, "target_version")
        negotiated = self._get(session, "negotiated_version")
        replay_verifiable = self._get(session, "replay_verifiable")
        if not replay_verifiable:
            return False
        expected = self.negotiate(source, target)
        return expected["negotiated_version"] == negotiated and expected["negotiation_status"] == self._get(session, "negotiation_status")

    def resolve_conflict(self, session: Any) -> dict[str, Any]:
        if self._get(session, "negotiation_status") != "conflicted":
            return {"resolution_status": "not_required", "reason": "session already resolved"}
        return {"resolution_status": "rejected", "reason": "no deterministic compatible version available"}

    def explain_negotiation(self, session: Any) -> str:
        return (
            f"source={self._get(session, 'source_version')}; "
            f"target={self._get(session, 'target_version')}; "
            f"negotiated={self._get(session, 'negotiated_version')}; "
            f"status={self._get(session, 'negotiation_status')}; "
            f"replay_verifiable={self._get(session, 'replay_verifiable')}"
        )

    @staticmethod
    def _get(item: Any, key: str) -> Any:
        return item[key] if isinstance(item, dict) else getattr(item, key)
