from pathlib import Path
import sys

# Add scripts to path for imports
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR / "scripts"))

from local_dr_backup import (
    BackupManifestInput,
    build_manifest,
    collect_asset_metadata,
    host_path_for_data_dir,
    sanitize_env_snapshot,
)


def test_backup_manifest_redacts_secrets_and_keeps_non_secret_settings(tmp_path: Path):
    env = {
        "ADMIN_TOKEN": "super-secret-token",
        "DATABASE_URL": "postgresql+asyncpg://user:password@postgres:5432/llm_gateway",
        "REDIS_URL": "redis://redis:6379/0",
        "HOST_PORT": "18080",
        "MODEL_FILE": "gemma-4-E4B-it-Q4_0.gguf",
    }

    lines = sanitize_env_snapshot(env)

    assert "ADMIN_TOKEN=__redacted__" in lines
    assert "HOST_PORT=18080" in lines
    assert "MODEL_FILE=gemma-4-E4B-it-Q4_0.gguf" in lines
    assert any(line.startswith("DATABASE_URL=postgresql+asyncpg://user:__redacted__@postgres:5432/llm_gateway") for line in lines)
    assert any(line.startswith("REDIS_URL=redis://redis:6379/0") for line in lines)

    dump_file = tmp_path / "db" / "postgres.dump"
    dump_file.parent.mkdir(parents=True)
    dump_file.write_text("dump", encoding="utf-8")
    config_file = tmp_path / "config" / "config.env"
    config_file.parent.mkdir(parents=True)
    config_file.write_text("HOST_PORT=18080\n", encoding="utf-8")

    manifest = build_manifest(
        BackupManifestInput(
            backup_dir=tmp_path,
            created_at="2026-05-07T12:00:00Z",
            app_version="1.2.3",
            alembic_revision="20260506_0018",
            stack_mode="local",
            env_file=".env.local",
            dump_file=str(dump_file),
            config_file=str(config_file),
            checksums_file=str(tmp_path / "checksums.sha256"),
            include_models=False,
            include_rag_files=True,
            redis_snapshot_included=False,
            assets=[
                collect_asset_metadata(dump_file, label="postgres_dump", included=True),
                collect_asset_metadata(config_file, label="config_snapshot", included=True),
            ],
        )
    )

    assert manifest["include_models"] is False
    assert manifest["include_rag_files"] is True
    assert manifest["files"]["postgres_dump"] == str(dump_file)
    assert manifest["assets"][0]["label"] == "postgres_dump"
    assert manifest["assets"][1]["label"] == "config_snapshot"


def test_host_path_for_rag_storage_dir_maps_container_mount_to_repo_root(tmp_path: Path):
    resolved = host_path_for_data_dir(tmp_path, "/data/rag_uploads/dr-test-1")

    assert resolved == tmp_path / "data" / "rag_uploads" / "dr-test-1"

