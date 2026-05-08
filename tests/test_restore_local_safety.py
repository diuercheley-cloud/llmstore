import subprocess
from pathlib import Path


def _build_fake_backup(tmp_dir: str, root_dir: Path) -> None:
    backup_dir = Path(tmp_dir)
    (backup_dir / "db").mkdir(parents=True, exist_ok=True)
    (backup_dir / "config").mkdir(parents=True, exist_ok=True)
    version = (root_dir / "VERSION").read_text(encoding="utf-8").strip()
    manifest = {
        "app_version": version,
        "alembic_revision": "",
        "include_models": False,
        "include_rag_files": False,
        "created_at": "2026-05-08T00:00:00Z",
    }
    (backup_dir / "manifest.json").write_text(__import__("json").dumps(manifest), encoding="utf-8")
    (backup_dir / "db" / "postgres.dump").write_bytes(b"fake-dump")
    (backup_dir / "config" / "config.env").write_text("ADMIN_TOKEN=[MASKED]\n", encoding="utf-8")

def test_restore_dry_run():
    """
    Validates that --dry-run works and does not attempt to restore.
    """
    root_dir = Path(__file__).resolve().parents[1]
    restore_script = root_dir / "scripts" / "restore-local.sh"
    
    import tempfile
    with tempfile.TemporaryDirectory() as tmp_dir:
        _build_fake_backup(tmp_dir, root_dir)
        
        # Now run restore with --dry-run
        result = subprocess.run(
            [str(restore_script), "--dry-run", tmp_dir],
            capture_output=True,
            text=True,
            cwd=str(root_dir)
        )
        
        assert "modo dry-run: validacao concluida com sucesso" in result.stdout
        assert result.returncode == 0

def test_restore_requires_confirmation():
    """
    Ensures that restore script doesn't proceed without --yes or interactive input.
    """
    root_dir = Path(__file__).resolve().parents[1]
    restore_script = root_dir / "scripts" / "restore-local.sh"

    import tempfile
    with tempfile.TemporaryDirectory() as tmp_dir:
        _build_fake_backup(tmp_dir, root_dir)
        
        # Run restore without --yes and with closed stdin
        result = subprocess.run(
            [str(restore_script), tmp_dir],
            capture_output=True,
            text=True,
            cwd=str(root_dir),
            input="", # empty input to simulate non-interactive or immediate failure
        )
        
        # It should either fail or wait for input. 
        # Since we gave empty input, it might fail or exit if it sees EOF.
        # Based on my change: if ! [[ "${response}" =~ ^[Yy]$ ]]; then exit 0; fi
        # Empty input will not match [Yy], so it should say "abortado pelo usuario".
        assert "abortado pelo usuario" in result.stdout or result.returncode != 0
