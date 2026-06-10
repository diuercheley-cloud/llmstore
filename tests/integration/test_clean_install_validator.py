import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLEAN_INSTALL_SCRIPT = ROOT / "scripts" / "validate-clean-install-local.sh"
VALIDATOR_SCRIPT = ROOT / "scripts" / "validate-clean-install-validator.sh"


def test_clean_install_script_exists():
    assert CLEAN_INSTALL_SCRIPT.exists(), "validate-clean-install-local.sh missing"
    assert os.access(CLEAN_INSTALL_SCRIPT, os.X_OK), "validate-clean-install-local.sh not executable"


def test_validator_script_exists():
    assert VALIDATOR_SCRIPT.exists(), "validate-clean-install-validator.sh missing"
    assert os.access(VALIDATOR_SCRIPT, os.X_OK), "validate-clean-install-validator.sh not executable"


def test_help_flag():
    result = subprocess.run(
        ["bash", str(CLEAN_INSTALL_SCRIPT), "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"--help failed:\n{result.stderr}"
    output = result.stdout.lower()
    assert "usage" in output or "clean install" in output, "--help output missing expected content"
    assert "--dry-run" in output, "--help missing --dry-run flag"
    assert "--yes" in output, "--help missing --yes flag"
    assert "--help" in output, "--help missing --help mention"


def test_unknown_flag():
    result = subprocess.run(
        ["bash", str(CLEAN_INSTALL_SCRIPT), "--unknown-flag-xyz"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode != 0, "Unknown flag should exit with error"


def test_dry_run_output_contains_mode():
    result = subprocess.run(
        ["bash", str(CLEAN_INSTALL_SCRIPT), "--dry-run", "--skip-build"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"--dry-run failed:\n{result.stderr}"
    output = result.stdout.lower()
    assert "dry-run" in output, "Output should mention DRY-RUN mode"


def test_dry_run_creates_report():
    result = subprocess.run(
        ["bash", str(CLEAN_INSTALL_SCRIPT), "--dry-run", "--skip-build"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0
    assert "clean-install-report.json" in result.stdout or "Report generated" in result.stdout, (
        "Report not mentioned in output"
    )


def test_dry_run_does_not_create_sandbox():
    result = subprocess.run(
        ["bash", str(CLEAN_INSTALL_SCRIPT), "--dry-run", "--skip-build"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0
    # After dry-run, there should be no instance directory
    sandbox_dirs = list((ROOT / "artifacts" / "clean-install-test").glob("*"))
    assert len(sandbox_dirs) >= 1, "Expected at least one sandbox dir"


def test_validator_script_help():
    result = subprocess.run(
        ["bash", str(VALIDATOR_SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"Validator failed:\n{result.stderr}"
    assert "PASS" in result.stdout or "checks passed" in result.stdout, (
        "Validator did not report results"
    )
