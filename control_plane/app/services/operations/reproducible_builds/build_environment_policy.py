from typing import Any

from app.models.operations.reproducible_builds import BuildEnvironmentConstraint
from app.services.operations.reproducible_builds.hash_utils import sha256_hex

BLOCKED_MARKERS = (
    "dynamic dependency install",
    "shell installer",
    "remote package manager",
    "external dependency resolution",
)


class BuildEnvironmentPolicyService:
    def validate_environment_constraints(self, payload: dict[str, Any]) -> BuildEnvironmentConstraint:
        logical_payload = {
            "client_id": str(payload["client_id"]),
            "constraint_name": payload["constraint_name"],
            "constraint_scope": payload["constraint_scope"],
            "required_determinism": payload.get("required_determinism", True),
            "offline_only": payload.get("offline_only", True),
            "external_network_allowed": payload.get("external_network_allowed", False),
            "external_dependency_resolution_allowed": payload.get("external_dependency_resolution_allowed", False),
        }
        constraint = BuildEnvironmentConstraint(
            id=sha256_hex({"kind": "build_environment_constraint_id", **logical_payload}),
            client_id=payload["client_id"],
            constraint_name=payload["constraint_name"],
            constraint_scope=payload["constraint_scope"],
            required_determinism=logical_payload["required_determinism"],
            offline_only=logical_payload["offline_only"],
            external_network_allowed=logical_payload["external_network_allowed"],
            external_dependency_resolution_allowed=logical_payload["external_dependency_resolution_allowed"],
            immutable_hash=sha256_hex({"kind": "build_environment_constraint_immutable", **logical_payload}),
        )
        constraint._logical_payload = logical_payload
        return constraint

    def enforce_offline_constraints(self, constraint: BuildEnvironmentConstraint) -> dict[str, Any]:
        blocked = constraint.external_network_allowed or constraint.external_dependency_resolution_allowed or not constraint.offline_only
        return {
            "allowed": not blocked,
            "verification_status": "blocked" if blocked else "passed",
            "reason": "external network or dependency resolution denied" if blocked else "offline-first constraints enforced",
        }

    def enforce_determinism_constraints(self, constraint: BuildEnvironmentConstraint, environment_summary: dict[str, Any] | None = None) -> dict[str, Any]:
        summary = environment_summary or {}
        markers = [item for item in summary.get("blocked_markers", []) if item in BLOCKED_MARKERS]
        blocked = not constraint.required_determinism or bool(markers)
        return {
            "allowed": not blocked,
            "verification_status": "blocked" if blocked else "passed",
            "reason": "determinism constraints violated" if blocked else "determinism constraints satisfied",
            "blocked_markers": markers,
        }

    def explain_constraints(self, constraint: BuildEnvironmentConstraint) -> dict[str, Any]:
        return {
            "constraint_name": constraint.constraint_name,
            "constraint_scope": constraint.constraint_scope,
            "offline_only": constraint.offline_only,
            "required_determinism": constraint.required_determinism,
            "notes": [
                "external_network_allowed=False enforced",
                "external_dependency_resolution_allowed=False enforced",
                "dynamic installers and remote package managers blocked",
            ],
        }
