from pathlib import Path

from scripts.local_dr_backup import host_path_for_data_dir, host_path_for_models_dir


def test_restore_local_script_mentions_clean_restore_flow():
    script = (Path(__file__).resolve().parents[1] / "scripts" / "restore-local.sh").read_text(encoding="utf-8")

    assert "pg_restore -U" in script
    assert "--clean --if-exists --no-owner --no-privileges" in script
    assert "docker compose up -d postgres redis" in script
    assert "include_rag_files" in script
    assert "include_models" in script


def test_restore_path_resolution_matches_bind_mounts(tmp_path: Path):
    assert host_path_for_models_dir(tmp_path, "/models") == tmp_path / "models"
    assert host_path_for_data_dir(tmp_path, "/data/rag_uploads") == tmp_path / "data" / "rag_uploads"
