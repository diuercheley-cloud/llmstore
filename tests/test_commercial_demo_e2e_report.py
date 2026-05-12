import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def latest_report_dir():
    base = ROOT / "artifacts" / "final-qa" / "commercial-demo-e2e"
    if not base.exists():
        return None
    subdirs = sorted([d for d in base.iterdir() if d.is_dir()])
    return subdirs[-1] if subdirs else None


def test_report_json_exists():
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory (run validation script first)")
    report_json = report_dir / "demo-e2e-report.json"
    assert report_json.exists(), "demo-e2e-report.json not found"
    assert report_json.stat().st_size > 0


def test_report_md_exists():
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory")
    report_md = report_dir / "demo-e2e-report.md"
    assert report_md.exists(), "demo-e2e-report.md not found"
    assert report_md.stat().st_size > 0


def test_report_is_valid_json():
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory")
    report_json = report_dir / "demo-e2e-report.json"
    data = json.loads(report_json.read_text(encoding="utf-8"))

    required = ["tool", "timestamp", "version", "base_url", "status", "counts", "results", "limitations"]
    for field in required:
        assert field in data, f"Missing required field: {field}"

    assert data["tool"] == "scripts/validate-commercial-demo-e2e-local.sh"
    assert data["status"] in ("DEMO_READY", "DEMO_READY_WITH_WARNINGS", "DEMO_FAILED")


def test_report_counts_match():
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory")
    report_json = report_dir / "demo-e2e-report.json"
    data = json.loads(report_json.read_text(encoding="utf-8"))

    c = data["counts"]
    n_pass = sum(1 for r in data["results"] if r.startswith("pass:"))
    n_fail = sum(1 for r in data["results"] if r.startswith("fail:"))
    n_warn = sum(1 for r in data["results"] if r.startswith("warn:"))

    assert c["pass"] >= n_pass, f"pass count ({c['pass']}) < actual ({n_pass})"
    assert c["fail"] >= n_fail
    assert c["warn"] >= n_warn


def test_report_has_logs_dir():
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory")
    logs_dir = report_dir / "logs"
    assert logs_dir.exists(), "logs/ directory not found"
    assert logs_dir.is_dir()


def test_report_has_limitations():
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory")
    report_json = report_dir / "demo-e2e-report.json"
    data = json.loads(report_json.read_text(encoding="utf-8"))
    assert len(data["limitations"]) > 0, "No limitations listed"
    assert any("PSP" in l for l in data["limitations"]), "Missing PSP limitation"


def test_report_no_secrets():
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory")

    for fname in ["demo-e2e-report.json", "demo-e2e-report.md"]:
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
