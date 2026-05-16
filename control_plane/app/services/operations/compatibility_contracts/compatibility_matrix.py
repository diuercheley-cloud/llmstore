from typing import Any

from app.services.operations.compatibility_contracts.semantic_versioning import SemanticVersioningService


class CompatibilityMatrixService:
    def __init__(self) -> None:
        self.semver = SemanticVersioningService()

    def build_matrix(self, source_version: str, target_version: str) -> dict[str, Any]:
        comparison = self.semver.compare_versions(source_version, target_version)
        backward = self.semver.is_backward_compatible(source_version, target_version)
        forward = self.semver.is_forward_compatible(source_version, target_version)
        bidirectional = self.semver.is_bidirectional_compatible(source_version, target_version)
        if bidirectional:
            compatibility_type = "bidirectional"
            compatibility_status = "compatible"
        elif backward:
            compatibility_type = "backward"
            compatibility_status = "compatible"
        elif forward:
            compatibility_type = "forward"
            compatibility_status = "warning"
        else:
            compatibility_type = "restricted"
            compatibility_status = "incompatible"
        return {
            "source_version": source_version,
            "target_version": target_version,
            "compatibility_type": compatibility_type,
            "compatibility_status": compatibility_status,
            "upgrade_supported": self.validate_upgrade_path(source_version, target_version),
            "downgrade_supported": self.validate_downgrade_path(source_version, target_version),
            "replay_safe": compatibility_status != "incompatible",
            "comparison": comparison,
        }

    def evaluate_compatibility(self, matrix: dict[str, Any]) -> dict[str, Any]:
        status = matrix["compatibility_status"]
        return {
            "allowed": status in {"compatible", "warning"},
            "blocked": status == "incompatible",
            "status": status,
        }

    def validate_upgrade_path(self, source: str, target: str) -> bool:
        comparison = self.semver.compare_versions(source, target)
        return comparison["order"] <= 0 and self.semver.is_backward_compatible(source, target)

    def validate_downgrade_path(self, source: str, target: str) -> bool:
        comparison = self.semver.compare_versions(source, target)
        return comparison["order"] >= 0 and self.semver.is_bidirectional_compatible(source, target)

    def explain_matrix(self, matrix: dict[str, Any]) -> str:
        return (
            f"type={matrix['compatibility_type']}; status={matrix['compatibility_status']}; "
            f"upgrade_supported={matrix['upgrade_supported']}; "
            f"downgrade_supported={matrix['downgrade_supported']}; "
            f"replay_safe={matrix['replay_safe']}"
        )
