from typing import Any

from app.models.operations.reproducible_builds import (
    REPRODUCIBILITY_STATUSES,
    REPRODUCIBLE_BUILD_SCOPES,
    ReproducibleBuildManifest,
)
from app.services.operations.reproducible_builds.hash_utils import (
    compute_build_manifest_hash,
    sha256_hex,
)


class ReproducibleBuildService:
    @staticmethod
    def _value(payload: dict[str, Any] | ReproducibleBuildManifest, key: str, default: Any = None) -> Any:
        if isinstance(payload, dict):
            return payload.get(key, default)
        return getattr(payload, key, default)

    def create_build_manifest(self, payload: dict[str, Any]) -> ReproducibleBuildManifest:
        self.validate_build_manifest(payload)
        logical_payload = {
            "client_id": str(payload["client_id"]),
            "build_name": payload["build_name"],
            "build_scope": payload["build_scope"],
            "source_reference": payload["source_reference"],
            "deterministic_version": payload["deterministic_version"],
            "build_environment_hash": payload["build_environment_hash"],
            "replay_safe": True,
        }
        manifest_hash = compute_build_manifest_hash(logical_payload)
        immutable_hash = sha256_hex({"kind": "reproducible_build_manifest_immutable", "build_manifest_hash": manifest_hash})
        manifest = ReproducibleBuildManifest(
            id=sha256_hex({"kind": "reproducible_build_manifest_id", **logical_payload}),
            client_id=payload["client_id"],
            build_name=payload["build_name"],
            build_scope=payload["build_scope"],
            source_reference=payload["source_reference"],
            deterministic_version=payload["deterministic_version"],
            build_environment_hash=payload["build_environment_hash"],
            build_manifest_hash=manifest_hash,
            reproducibility_status=payload.get("reproducibility_status", "proposed"),
            replay_safe=True,
            immutable_hash=immutable_hash,
        )
        manifest._logical_payload = logical_payload
        return manifest

    def validate_build_manifest(self, payload: dict[str, Any] | ReproducibleBuildManifest) -> dict[str, Any]:
        build_scope = self._value(payload, "build_scope")
        reproducibility_status = self._value(payload, "reproducibility_status", "proposed")
        replay_safe = self._value(payload, "replay_safe", True)
        build_environment_hash = self._value(payload, "build_environment_hash")

        if build_scope not in REPRODUCIBLE_BUILD_SCOPES:
            raise ValueError("unsupported build scope")
        if reproducibility_status not in REPRODUCIBILITY_STATUSES:
            raise ValueError("unsupported reproducibility status")
        if not replay_safe:
            raise ValueError("replay_safe is mandatory")
        if not build_environment_hash:
            raise ValueError("build_environment_hash is mandatory")

        logical_payload = getattr(payload, "_logical_payload", None) or {
            "client_id": str(self._value(payload, "client_id")),
            "build_name": self._value(payload, "build_name"),
            "build_scope": build_scope,
            "source_reference": self._value(payload, "source_reference"),
            "deterministic_version": self._value(payload, "deterministic_version"),
            "build_environment_hash": build_environment_hash,
            "replay_safe": True,
        }
        replayed_hash = compute_build_manifest_hash(logical_payload)
        original_hash = getattr(payload, "build_manifest_hash", replayed_hash)
        status = "reproducible" if replayed_hash == original_hash and reproducibility_status != "revoked" else "blocked"
        if hasattr(payload, "reproducibility_status"):
            payload.reproducibility_status = status
        return {
            "valid": replayed_hash == original_hash,
            "deterministic_only": True,
            "replay_safe": True,
            "original_hash": original_hash,
            "replayed_hash": replayed_hash,
            "reproducibility_status": status,
        }

    def revoke_build_manifest(self, manifest: ReproducibleBuildManifest, reason: str = "manual revoke") -> dict[str, Any]:
        manifest.reproducibility_status = "revoked"
        manifest.replay_safe = False
        return {
            "status": "revoked",
            "reason": reason,
            "replay_safe": False,
            "deterministic_only": True,
        }

    def explain_build_manifest(self, manifest: ReproducibleBuildManifest) -> dict[str, Any]:
        return {
            "build_name": manifest.build_name,
            "build_scope": manifest.build_scope,
            "source_reference": manifest.source_reference,
            "deterministic_version": manifest.deterministic_version,
            "replay_safe": manifest.replay_safe,
            "offline_first": True,
            "notes": [
                "deterministic verification only",
                "no real external build execution",
                "build metadata replay-safe",
            ],
        }
