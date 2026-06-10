import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate-real-restore-rollback-local.sh"
REPORT_BASE = ROOT / "artifacts" / "restore-rollback-test"


def latest_report_dir():
    if not REPORT_BASE.exists():
        return None
    subdirs = sorted([d for d in REPORT_BASE.iterdir() if d.is_dir()])
    return subdirs[-1] if subdirs else None


def test_report_json_exists_after_dry_run():
    result = subprocess.run(
        ["bash", str(SCRIPT), "--dry-run"],
        cwd=ROOT, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0

    report_dir = latest_report_dir()
    assert report_dir is not None, "No report directory found"
    report_json = report_dir / "restore-rollback-report.json"
    assert report_json.exists(), "restore-rollback-report.json not found"
    assert report_json.stat().st_size > 0, "report is empty"


def test_report_md_exists_after_dry_run():
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory")
    report_md = report_dir / "restore-rollback-report.md"
    assert report_md.exists(), "restore-rollback-report.md not found"
    assert report_md.stat().st_size > 0, "report md is empty"


def test_report_is_valid_json():
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory")
    report_json = report_dir / "restore-rollback-report.json"
    data = json.loads(report_json.read_text(encoding="utf-8"))

    required = ["tool", "timestamp", "version", "dry_run", "from_version", "to_version",
                "results", "failures", "warnings", "safety_guarantees"]
    for field in required:
        assert field in data, f"Missing required field: {field}"
    assert data["dry_run"] is True
    assert "ROLLBACK LOCAL" not in json.dumps(data), "Sensitive content in report"


def test_report_no_secrets():
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory")

    for fname in ["restore-rollback-report.json", "restore-rollback-report.md"]:
        fp = report_dir / fname
        if not fp.exists():
            continue
        content = fp.read_text(encoding="utf-8")
        for pat in ["sk-", "ghp_", "ADMIN_TOKEN=", "JWT_SECRET=", "-----BEGIN"]:
            if pat in content:
                for allow in ["__redacted__", "sk-demo", "sk-local-example"]:
                    if allow in content:
                        break
                else:
                    assert False, f"Secret pattern '{pat}' in {fname}"


def test_report_has_logs_dir():
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory")
    logs_dir = report_dir / "logs"
    assert logs_dir.exists(), "logs/ directory not found"


def test_report_safety_guarantees():
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory")
    report_json = report_dir / "restore-rollback-report.json"
    data = json.loads(report_json.read_text(encoding="utf-8"))

    sg = data["safety_guarantees"]
    assert isinstance(sg, dict)
    assert "backup_required_before_upgrade" in sg
    assert "rollback_strong_confirmation" in sg
    assert "git_clean_check" in sg
    assert "dry_run_supported" in sg
    assert sg["dry_run_supported"] is True


def test_report_version():
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory")
    actual_version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    report_json = report_dir / "restore-rollback-report.json"
    data = json.loads(report_json.read_text(encoding="utf-8"))
    assert data["version"] == actual_version, f"Version mismatch: {data['version']} vs {actual_version}"
