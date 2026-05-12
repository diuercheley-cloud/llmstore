import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
VALIDATE_SCRIPT = ROOT / "scripts" / "validate-v1.7-final-local.sh"
REPORT_SCRIPT = ROOT / "scripts" / "validate-v1.7-final-report.sh"
CHECK_SECRETS = ROOT / "scripts" / "check-secrets.sh"
ARTIFACTS_BASE = ROOT / "artifacts" / "v1.7-final-validation"
VERSION = "v1.7.0-local-ai-appliance"
RELEASE_DIR = ROOT / "releases" / VERSION


def latest_report_dir():
    if not ARTIFACTS_BASE.exists():
        return None
    subdirs = sorted([d for d in ARTIFACTS_BASE.iterdir() if d.is_dir()])
    return subdirs[-1] if subdirs else None


def test_validate_script_exists():
    assert VALIDATE_SCRIPT.exists(), "validate-v1.7-final-local.sh not found"
    assert os.access(VALIDATE_SCRIPT, os.X_OK), "script not executable"


def test_report_script_exists():
    assert REPORT_SCRIPT.exists(), "validate-v1.7-final-report.sh not found"
    assert os.access(REPORT_SCRIPT, os.X_OK), "report script not executable"


def test_check_secrets_exists():
    assert CHECK_SECRETS.exists(), "check-secrets.sh not found"


def test_validate_script_runs_quick():
    """Must complete in --quick mode."""
    result = subprocess.run(
        ["bash", str(VALIDATE_SCRIPT), "--quick"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    print(f"STDOUT:\n{result.stdout[-2000:]}")
    assert result.returncode in (0,), (
        f"Validate script failed with exit {result.returncode}"
    )


def test_report_json_exists():
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory found")
    fp = report_dir / "v1.7-final-validation.json"
    assert fp.exists(), "v1.7-final-validation.json not found"
    assert fp.stat().st_size > 0


def test_report_md_exists():
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory found")
    fp = report_dir / "v1.7-final-validation.md"
    assert fp.exists(), "v1.7-final-validation.md not found"
    assert fp.stat().st_size > 0


def test_report_json_valid():
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory found")
    fp = report_dir / "v1.7-final-validation.json"
    data = json.loads(fp.read_text(encoding="utf-8"))

    required = ["report_type", "version", "final_status", "critical_fails",
                 "blocking_warnings", "nonblocking_warnings", "generated_at"]
    for field in required:
        assert field in data, f"Missing field: {field}"

    assert data["report_type"] == "v1.7-final-validation"
    valid_statuses = ["V1_7_READY", "V1_7_READY_WITH_WARNINGS", "V1_7_NOT_READY"]
    assert data["final_status"] in valid_statuses, (
        f"Invalid status: {data['final_status']}"
    )


def test_report_consistent_status():
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory found")
    fp = report_dir / "v1.7-final-validation.json"
    data = json.loads(fp.read_text(encoding="utf-8"))

    cf = data.get("critical_fails", 0)
    bw = data.get("blocking_warnings", 0)
    nw = data.get("nonblocking_warnings", 0)
    status = data.get("final_status", "")

    if cf > 0 or bw > 0:
        assert status == "V1_7_NOT_READY", (
            f"Has {cf} critical fails and {bw} blocking warns but status={status}"
        )
    elif nw > 0:
        assert status == "V1_7_READY_WITH_WARNINGS", (
            f"Has {nw} non-blocking warns but status={status}"
        )
    else:
        assert status == "V1_7_READY", (
            f"No issues but status={status}"
        )


def test_logs_exist():
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory found")
    logs = report_dir / "logs"
    assert logs.exists(), "logs directory not found"
    log_files = list(logs.iterdir())
    assert len(log_files) > 0, "No log files found"


def test_no_critical_fails():
    """Non-blocking: report if critical fails exist."""
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory found")
    fp = report_dir / "v1.7-final-validation.json"
    data = json.loads(fp.read_text(encoding="utf-8"))
    cf = data.get("critical_fails", 0)
    if cf > 0:
        pytest.fail(f"Report has {cf} critical fails: {data.get('critical_fail_list', [])}")


def test_report_has_limitations():
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory found")
    fp = report_dir / "v1.7-final-validation.json"
    data = json.loads(fp.read_text(encoding="utf-8"))
    limitations = data.get("limitations_out_of_scope", [])
    assert len(limitations) > 0, "No limitations_out_of_scope"
    has_psp = any("PSP" in l for l in limitations)
    assert has_psp, "PSP/PIX not in limitations"


def test_report_script_runs():
    result = subprocess.run(
        ["bash", str(REPORT_SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    print(f"STDOUT:\n{result.stdout}")
    assert result.returncode == 0, (
        f"Report validation script failed:\n{result.stdout}"
    )


def test_release_dir_exists():
    assert RELEASE_DIR.exists(), f"releases/{VERSION} not found"


def test_release_has_5_files():
    files = [f for f in RELEASE_DIR.iterdir() if f.is_file()]
    assert len(files) == 5, (
        f"Expected 5 files, found {len(files)}: {[f.name for f in files]}"
    )
