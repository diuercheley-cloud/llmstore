import json
from unittest.mock import AsyncMock

import pytest
import yaml
from app.services.backup.backup_service import BackupService


@pytest.mark.asyncio
async def test_backup_redaction_and_exclusion(tmp_path, monkeypatch):
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", "a" * 32)
    monkeypatch.setenv("BACKUP_SIGNING_KEY", "b" * 32)

    # Set up fake repo root
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".env").write_text("JWT_SECRET=secret\nPORT=8080", encoding="utf-8")
    (repo_root / ".env.local").write_text("DB_PASSWORD=pass\nHOST=localhost", encoding="utf-8")
    (repo_root / "VERSION").write_text("1.0.0", encoding="utf-8")

    config_dir = repo_root / "config"
    config_dir.mkdir()
    (config_dir / "app.yaml").write_text(
        "port: 8080\napi_key: my-secret-key\nnested:\n  secret_token: stoken", encoding="utf-8"
    )

    # Mock database session (just needs to return empty results for queries)
    from unittest.mock import MagicMock

    mock_db = AsyncMock()
    mock_db.add = MagicMock()  # db.add() is synchronous in SQLAlchemy
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)

    service = BackupService(mock_db)
    service.repo_root = repo_root
    service.backup_root = tmp_path / "backups"
    service.backup_root.mkdir()

    manifest = await service.create_backup()

    # Check manifest fields
    assert ".env" in manifest.excluded_sensitive_files
    assert ".env.local" in manifest.excluded_sensitive_files
    assert any("api_key" in k for k in manifest.redacted_config_keys)
    assert any("secret_token" in k for k in manifest.redacted_config_keys)

    # Read the generated configs.json from payload parts
    payload_parts = await service._build_payload_parts()
    configs_json = json.loads(payload_parts["configs.json"].decode("utf-8"))

    # Check that .env and .env.local are NOT in the files
    file_paths = [f["path"] for f in configs_json["files"]]
    assert ".env" not in file_paths
    assert ".env.local" not in file_paths
    assert "VERSION" in file_paths
    assert "config/app.yaml" in file_paths

    # Check redaction in app.yaml
    app_yaml_entry = next(f for f in configs_json["files"] if f["path"] == "config/app.yaml")
    app_yaml_parsed = yaml.safe_load(app_yaml_entry["content"])
    assert app_yaml_parsed["port"] == 8080
    assert app_yaml_parsed["api_key"] == "REDACTED"
    assert app_yaml_parsed["nested"]["secret_token"] == "REDACTED"
