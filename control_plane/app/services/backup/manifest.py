import hashlib
import json
from pathlib import Path

from app.schemas.backup import BackupComponent, BackupManifest


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


class ManifestService:
    def build_components(self, payload_parts: dict[str, bytes]) -> list[BackupComponent]:
        labels = {
            "database.json": ("database", "Logical database snapshot for supported DR tables"),
            "db.dump": ("database", "Complete native database dump"),
            "configs.json": ("configs", "Environment and config file snapshot"),
            "feature_flags.json": ("feature_flags", "Feature flag registry snapshot"),
            "agents.json": ("agents", "Agent definitions and registry snapshot"),
            "workflows.json": ("workflows", "Workflow definitions and executions snapshot"),
            "embeddings_metadata.json": ("embeddings_metadata", "Embedding metadata snapshot"),
        }
        components: list[BackupComponent] = []
        for file_name, payload in payload_parts.items():
            if file_name.endswith(".json"):
                try:
                    parsed = json.loads(payload.decode("utf-8"))
                    item_count = parsed.get("item_count")
                    if item_count is None:
                        item_count = len(parsed.get("files", []))
                except Exception:
                    item_count = 1
            else:
                item_count = 1

            name, description = labels.get(file_name, ("unknown", "Unknown component"))
            components.append(
                BackupComponent(
                    name=name,
                    description=description,
                    item_count=item_count,
                    data_hash=_sha256_bytes(payload),
                    file_name=file_name,
                )
            )
        return components

    def read(self, backup_root: Path, backup_id: str) -> BackupManifest:
        from .errors import BackupManifestError

        manifest_path = backup_root / backup_id / "manifest.json"
        if not manifest_path.exists():
            raise BackupManifestError(
                f"Backup manifest not found: {backup_id}", details={"backup_id": backup_id}
            )
        try:
            return BackupManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise BackupManifestError(
                f"Backup manifest is corrupted: {backup_id}",
                details={"backup_id": backup_id, "path": str(manifest_path)},
            ) from exc

    def write(self, backup_root: Path, manifest: BackupManifest) -> None:
        target_dir = backup_root / manifest.backup_id
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "manifest.json").write_text(
            json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True),
            encoding="utf-8",
        )


# Backward compatibility
class ManifestBuilder:
    @staticmethod
    def build_components(payload_parts: dict[str, bytes]) -> list[BackupComponent]:
        return ManifestService().build_components(payload_parts)


class ManifestReader:
    @staticmethod
    def read(backup_root: Path, backup_id: str) -> BackupManifest:
        return ManifestService().read(backup_root, backup_id)

    @staticmethod
    def write(backup_root: Path, manifest: BackupManifest) -> None:
        return ManifestService().write(backup_root, manifest)
