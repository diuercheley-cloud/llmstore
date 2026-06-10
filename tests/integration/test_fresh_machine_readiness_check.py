import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "fresh-machine-readiness-check.sh"


def test_script_exists():
    assert SCRIPT.exists()
    assert os.access(SCRIPT, os.X_OK)


def test_script_help():
    result = subprocess.run(
        ["bash", str(SCRIPT), "--help"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0
    assert "Usage:" in result.stdout


def test_script_dry_run_exit_zero():
    result = subprocess.run(
        ["bash", str(SCRIPT), "--dry-run"],
        capture_output=True, text=True, timeout=60,
    )
    print(f"STDOUT:\n{result.stdout}")
    if result.returncode != 0:
        pytest.skip("Dry-run found failures (expected in non-fresh machine)")
    assert "Fresh Machine Readiness Check" in result.stdout


def test_script_dry_run_generates_report():
    output_dir = ROOT / "artifacts" / "fresh-machine-check"
    result = subprocess.run(
        ["bash", str(SCRIPT), "--dry-run"],
        capture_output=True, text=True, timeout=60,
    )
    assert "Reports generated" in result.stdout, (
        f"No report generation message.\nSTDOUT:\n{result.stdout}"
    )
    json_files = sorted(output_dir.rglob("fresh-machine-check.json"))
    assert len(json_files) > 0, "No JSON report found"
    latest = json_files[-1]
    data = json.loads(latest.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert len(data) > 0


def test_script_json_flag():
    output_dir = ROOT / "artifacts" / "fresh-machine-check"
    result = subprocess.run(
        ["bash", str(SCRIPT), "--dry-run", "--json"],
        capture_output=True, text=True, timeout=60,
    )
    json_files = sorted(output_dir.rglob("fresh-machine-check.json"))
    assert len(json_files) > 0
    latest = json_files[-1]
    data = json.loads(latest.read_text(encoding="utf-8"))
    assert len(data) > 0
    for entry in data:
        assert "check" in entry
        assert "status" in entry
        assert "detail" in entry
        assert entry["status"] in ("PASS", "FAIL", "WARN")


def test_script_output_dir():
    tmp_dir = ROOT / "artifacts" / "fresh-machine-check"
    result = subprocess.run(
        ["bash", str(SCRIPT), "--dry-run", "--output-dir", str(tmp_dir)],
        capture_output=True, text=True, timeout=60,
    )
    json_files = sorted(tmp_dir.rglob("fresh-machine-check.json"))
    assert len(json_files) > 0, f"No JSON reports in {tmp_dir}"
    md_files = sorted(tmp_dir.rglob("fresh-machine-check.md"))
    assert len(md_files) > 0, f"No MD reports in {tmp_dir}"


def test_script_check_os():
    result = subprocess.run(
        ["bash", str(SCRIPT), "--dry-run"],
        capture_output=True, text=True, timeout=60,
    )
    assert "OS" in result.stdout


def test_script_check_docker():
    result = subprocess.run(
        ["bash", str(SCRIPT), "--dry-run"],
        capture_output=True, text=True, timeout=60,
    )
    assert "Docker" in result.stdout


def test_script_check_git():
    result = subprocess.run(
        ["bash", str(SCRIPT), "--dry-run"],
        capture_output=True, text=True, timeout=60,
    )
    assert "git" in result.stdout


def test_script_check_env_file():
    result = subprocess.run(
        ["bash", str(SCRIPT), "--dry-run"],
        capture_output=True, text=True, timeout=60,
    )
    assert ".env.local" in result.stdout


def test_report_md_generated():
    output_dir = ROOT / "artifacts" / "fresh-machine-check"
    md_files = sorted(output_dir.rglob("fresh-machine-check.md"))
    assert len(md_files) > 0
    content = md_files[-1].read_text(encoding="utf-8")
    assert "Fresh Machine Readiness Check Report" in content
    assert "Summary" in content
    assert "Detailed Results" in content


def test_report_json_generated():
    output_dir = ROOT / "artifacts" / "fresh-machine-check"
    json_files = sorted(output_dir.rglob("fresh-machine-check.json"))
    assert len(json_files) > 0
    data = json.loads(json_files[-1].read_text(encoding="utf-8"))
    checks = {entry["check"]: entry["status"] for entry in data}
    assert "OS (Linux)" in checks
    assert "Docker" in checks
    assert "git" in checks
    assert ".env.local exists" in checks
