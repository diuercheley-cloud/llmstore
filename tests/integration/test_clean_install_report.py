import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CLEAN_INSTALL_SCRIPT = ROOT / "scripts" / "validate-clean-install-local.sh"
CLEAN_INSTALL_BASE = ROOT / "artifacts" / "clean-install-test"


def latest_report_dir():
    if not CLEAN_INSTALL_BASE.exists():
        return None
    subdirs = sorted([d for d in CLEAN_INSTALL_BASE.iterdir() if d.is_dir()])
    return subdirs[-1] if subdirs else None


def test_report_json_exists_after_dry_run():
    result = subprocess.run(
        ["bash", str(CLEAN_INSTALL_SCRIPT), "--dry-run", "--skip-build"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0

    report_dir = latest_report_dir()
    assert report_dir is not None, "No report directory found"
    report_json = report_dir / "clean-install-report.json"
    assert report_json.exists(), "clean-install-report.json not found"
    assert report_json.stat().st_size > 0, "clean-install-report.json is empty"


def test_report_md_exists_after_dry_run():
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory found")
    report_md = report_dir / "clean-install-report.md"
    assert report_md.exists(), "clean-install-report.md not found"
    assert report_md.stat().st_size > 0, "clean-install-report.md is empty"


def test_report_is_valid_json():
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory found")
    report_json = report_dir / "clean-install-report.json"
    data = json.loads(report_json.read_text(encoding="utf-8"))

    required_fields = [
        "tool",
        "timestamp",
        "version",
        "dry_run",
        "overall_status",
        "steps",
        "failures",
        "warnings",
    ]
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"

    assert data["tool"] == "scripts/validators/validate-clean-install-local.sh"
    assert data["dry_run"] is True
    assert "overall_label" in data


def test_report_has_logs_dir():
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory found")
    logs_dir = report_dir / "logs"
    assert logs_dir.exists(), "logs/ directory not found in report"
    assert logs_dir.is_dir(), "logs/ is not a directory"


def test_report_no_secrets():
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory found")

    for fname in ["clean-install-report.json", "clean-install-report.md"]:
        fp = report_dir / fname
        if not fp.exists():
            continue
        content = fp.read_text(encoding="utf-8")

        secret_patterns = ["sk-", "ghp_", "ADMIN_TOKEN=", "JWT_SECRET=", "-----BEGIN"]
        for pat in secret_patterns:
            if pat in content:
                for allow in ["__redacted__", "sk-demo", "sk-local-example"]:
                    if allow in content:
                        break
                else:
                    assert False, f"Secret pattern '{pat}' found in {fname}"


def test_report_version_matches_repo():
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory found")

    actual_version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    report_json = report_dir / "clean-install-report.json"
    data = json.loads(report_json.read_text(encoding="utf-8"))

    assert data["version"] == actual_version, (
        f"Report version '{data['version']}' != repo version '{actual_version}'"
    )
