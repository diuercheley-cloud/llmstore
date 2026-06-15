import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate-real-restore-rollback-local.sh"


def test_script_exists():
    assert SCRIPT.exists(), "validate-real-restore-rollback-local.sh missing"
    assert os.access(SCRIPT, os.X_OK), "script not executable"


def test_help_flag():
    result = subprocess.run(
        ["bash", str(SCRIPT), "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"--help failed:\n{result.stderr}"
    output = result.stdout.lower()
    assert "usage" in output or "restore" in output
    assert "--dry-run" in output
    assert "--yes" in output
    assert "--to-version" in output
    assert "--from-version" in output


def test_unknown_flag():
    result = subprocess.run(
        ["bash", str(SCRIPT), "--unknown-flag"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode != 0, "unknown flag should fail"


def test_dry_run_default_mode():
    result = subprocess.run(
        ["bash", str(SCRIPT), "--dry-run"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"--dry-run failed:\n{result.stderr}"
    assert "DRY-RUN" in result.stdout, "Output should mention DRY-RUN mode"


def test_dry_run_checks_scripts_exist():
    result = subprocess.run(
        ["bash", str(SCRIPT), "--dry-run"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0
    for script in ["backup-local.sh", "restore-local.sh", "upgrade-local.sh", "rollback-local.sh"]:
        assert script in result.stdout, f"{script} not mentioned in output"


def test_dry_run_validates_rollback_confirmation():
    result = subprocess.run(
        ["bash", str(SCRIPT), "--dry-run"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0
    assert "ROLLBACK LOCAL" in result.stdout or "confirmation" in result.stdout.lower(), (
        "Rollback confirmation not mentioned"
    )


def test_dry_run_validates_upgrade_backup_requirement():
    result = subprocess.run(
        ["bash", str(SCRIPT), "--dry-run"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0
    assert "SKIP_BACKUP" in result.stdout or "backup" in result.stdout.lower(), (
        "Backup requirement not mentioned"
    )


def test_dry_run_generates_report():
    result = subprocess.run(
        ["bash", str(SCRIPT), "--dry-run"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0
    assert "restore-rollback-report.json" in result.stdout or "Report generated" in result.stdout
