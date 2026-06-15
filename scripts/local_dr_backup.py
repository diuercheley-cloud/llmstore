from __future__ import annotations

import json
import os
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

SENSITIVE_KEY_PATTERNS = (
    "TOKEN",
    "PASSWORD",
    "SECRET",
    "API_KEY",
    "JWT_SECRET",
)

ALWAYS_REDACT_URL_KEYS = {
    "DATABASE_URL",
    "REDIS_URL",
}

REDACTED_VALUE = "__redacted__"

DEFAULT_MANIFEST_NAME = "manifest.json"
DEFAULT_DUMP_NAME = "postgres.dump"
DEFAULT_CONFIG_NAME = "config.env"
DEFAULT_CHECKSUM_NAME = "checksums.sha256"


def parse_env_file(path: os.PathLike[str] | str) -> dict[str, str]:
    data: dict[str, str] = {}
    path_obj = Path(path)
    if not path_obj.exists():
        return data
    for raw_line in path_obj.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = raw_line.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def _looks_sensitive(key: str) -> bool:
    upper = key.upper()
    return any(pattern in upper for pattern in SENSITIVE_KEY_PATTERNS)


def redact_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return REDACTED_VALUE
    if not parsed.scheme:
        return REDACTED_VALUE
    netloc = parsed.hostname or ""
    if parsed.port is not None:
        netloc = f"{netloc}:{parsed.port}"
    if parsed.username:
        netloc = f"{parsed.username}:{REDACTED_VALUE}@{netloc}"
    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))


def sanitize_env_snapshot(env: dict[str, str]) -> list[str]:
    lines: list[str] = []
    for key in sorted(env):
        value = env[key]
        if key in ALWAYS_REDACT_URL_KEYS:
            lines.append(f"{key}={redact_url(value)}")
            continue
        if key == "LMSTUDIO_API_KEY":
            lines.append(f"{key}={REDACTED_VALUE}")
            continue
        if _looks_sensitive(key):
            lines.append(f"{key}={REDACTED_VALUE}")
            continue
        lines.append(f"{key}={value}")
    return lines


def host_path_for_data_dir(
    root_dir: os.PathLike[str] | str, storage_dir: str | None
) -> Path | None:
    if not storage_dir:
        return None
    root = Path(root_dir)
    storage_dir = storage_dir.strip()
    if storage_dir.startswith("/data/"):
        return root / "data" / storage_dir.removeprefix("/data/")
    if storage_dir == "/data":
        return root / "data"
    if storage_dir.startswith("./"):
        return root / storage_dir.removeprefix("./")
    if storage_dir.startswith("/"):
        return Path(storage_dir)
    return root / storage_dir


def host_path_for_models_dir(
    root_dir: os.PathLike[str] | str, models_dir: str | None
) -> Path | None:
    if not models_dir:
        return None
    root = Path(root_dir)
    models_dir = models_dir.strip()
    if models_dir == "/models":
        return root / "models"
    if models_dir.startswith("./"):
        return root / models_dir.removeprefix("./")
    if models_dir.startswith("/"):
        return Path(models_dir)
    return root / models_dir


def _file_metadata(path: Path) -> dict[str, object]:
    stat = path.stat()
    return {
        "type": "file",
        "path": str(path),
        "name": path.name,
        "size_bytes": stat.st_size,
        "mtime": int(stat.st_mtime),
    }


def _directory_metadata(path: Path) -> dict[str, object]:
    file_count = 0
    total_bytes = 0
    for item in path.rglob("*"):
        if item.is_file():
            file_count += 1
            total_bytes += item.stat().st_size
    return {
        "type": "directory",
        "path": str(path),
        "name": path.name,
        "file_count": file_count,
        "size_bytes": total_bytes,
    }


def collect_asset_metadata(path: Path | None, *, label: str, included: bool) -> dict[str, object]:
    asset: dict[str, object] = {
        "label": label,
        "included": included,
        "exists": False,
    }
    if path is None:
        return asset
    asset["path"] = str(path)
    asset["exists"] = path.exists()
    if path.is_file():
        asset.update(_file_metadata(path))
    elif path.is_dir():
        asset.update(_directory_metadata(path))
    return asset


@dataclass(slots=True)
class BackupManifestInput:
    backup_dir: Path
    created_at: str
    app_version: str
    alembic_revision: str
    stack_mode: str
    env_file: str
    dump_file: str
    config_file: str
    checksums_file: str
    include_models: bool
    include_rag_files: bool
    redis_snapshot_included: bool
    assets: list[dict[str, object]]


def build_manifest(payload: BackupManifestInput) -> dict[str, object]:
    return {
        "created_at": payload.created_at,
        "app_version": payload.app_version,
        "alembic_revision": payload.alembic_revision,
        "stack_mode": payload.stack_mode,
        "env_file": payload.env_file,
        "backup_dir": str(payload.backup_dir),
        "include_models": payload.include_models,
        "include_rag_files": payload.include_rag_files,
        "redis_snapshot_included": payload.redis_snapshot_included,
        "files": {
            "postgres_dump": payload.dump_file,
            "config_snapshot": payload.config_file,
            "checksums": payload.checksums_file,
        },
        "assets": payload.assets,
    }


def dump_manifest(manifest: dict[str, object], path: os.PathLike[str] | str) -> None:
    Path(path).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_manifest(path: os.PathLike[str] | str) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def iter_asset_paths(manifest: dict[str, object]) -> Iterable[Path]:
    assets = manifest.get("assets", [])
    if not isinstance(assets, list):
        return []
    paths: list[Path] = []
    for asset in assets:
        if isinstance(asset, dict) and asset.get("included") and asset.get("path"):
            paths.append(Path(str(asset["path"])))
    return paths


def restore_targets(
    manifest: dict[str, object], root_dir: os.PathLike[str] | str
) -> list[tuple[Path, Path]]:
    root = Path(root_dir)
    targets: list[tuple[Path, Path]] = []
    for asset in manifest.get("assets", []):
        if not isinstance(asset, dict) or not asset.get("included"):
            continue
        label = str(asset.get("label", ""))
        src_path = asset.get("path")
        if not src_path:
            continue
        src = Path(str(src_path))
        if label == "rag_files":
            targets.append(
                (src, host_path_for_data_dir(root, str(asset.get("storage_dir", ""))) or src)
            )
        elif label == "model_files":
            targets.append(
                (src, host_path_for_models_dir(root, str(asset.get("models_dir", ""))) or src)
            )
    return targets
