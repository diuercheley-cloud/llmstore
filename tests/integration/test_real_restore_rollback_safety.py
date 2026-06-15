import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate-real-restore-rollback-local.sh"


def test_upgrade_script_has_backup_requirement():
    """Verify upgrade-local.sh requires backup or --skip-backup --yes."""
    content = (ROOT / "scripts" / "upgrade-local.sh").read_text(encoding="utf-8")
    assert "SKIP_BACKUP" in content, "upgrade-local.sh missing SKIP_BACKUP logic"


def test_rollback_script_has_strong_confirmation():
    """Verify rollback-local.sh requires typing 'ROLLBACK LOCAL'."""
    content = (ROOT / "scripts" / "rollback-local.sh").read_text(encoding="utf-8")
    assert "ROLLBACK LOCAL" in content, "rollback-local.sh missing strong confirmation"


def test_upgrade_script_checks_working_tree():
    """Verify upgrade-local.sh checks for clean working tree."""
    content = (ROOT / "scripts" / "upgrade-local.sh").read_text(encoding="utf-8")
    assert "git diff-index" in content or "git diff" in content, (
        "upgrade-local.sh missing working tree check"
    )


def test_rollback_script_checks_working_tree():
    """Verify rollback-local.sh checks for clean working tree."""
    content = (ROOT / "scripts" / "rollback-local.sh").read_text(encoding="utf-8")
    assert "git diff-index" in content or "git diff" in content, (
        "rollback-local.sh missing working tree check"
    )


def test_restore_script_has_dry_run():
    """Verify restore-local.sh supports --dry-run."""
    content = (ROOT / "scripts" / "restore-local.sh").read_text(encoding="utf-8")
    assert "--dry-run" in content, "restore-local.sh missing --dry-run"


def test_backup_script_has_exclusions():
    """Verify backup-local.sh excludes models and RAG by default."""
    content = (ROOT / "scripts" / "backup-local.sh").read_text(encoding="utf-8")
    assert "include_models" in content, "backup-local.sh missing model exclusion"
    assert "include_rag_files" in content, "backup-local.sh missing RAG exclusion"


def test_dry_run_does_not_modify_repo():
    """Verify --dry-run does not modify the repo."""
    original_version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()

    result = subprocess.run(
        ["bash", str(SCRIPT), "--dry-run"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0

    current_version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    assert current_version == original_version, "VERSION was modified by dry-run"


def test_all_scripts_executable():
    scripts = [
        "scripts/backup/backup-local.sh",
        "scripts/backup/restore-local.sh",
        "scripts/deploy/upgrade-local.sh",
        "scripts/dev/rollback-local.sh",
        "scripts/validators/post-upgrade-smoke-local.sh",
        "scripts/validators/validate-upgrade-migrations-local.sh",
    ]
    for s in scripts:
        path = ROOT / s
        assert path.exists(), f"{s} missing"
        assert path.stat().st_mode & 0o111, f"{s} not executable"
