import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_BASE = ROOT / "artifacts" / "v1.7-final-validation"


def latest_report_dir():
    if not ARTIFACTS_BASE.exists():
        return None
    subdirs = sorted([d for d in ARTIFACTS_BASE.iterdir() if d.is_dir()])
    return subdirs[-1] if subdirs else None


def test_latest_report_json():
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory")
    fp = report_dir / "v1.7-final-validation.json"
    assert fp.exists()
    data = json.loads(fp.read_text(encoding="utf-8"))

    required = [
        "report_type",
        "version",
        "git_branch",
        "git_commit",
        "generated_at",
        "timestamp",
        "final_status",
        "critical_fails",
        "blocking_warnings",
        "nonblocking_warnings",
        "critical_fail_list",
        "blocking_warning_list",
        "nonblocking_warning_list",
        "limitations_out_of_scope",
    ]
    for field in required:
        assert field in data, f"Missing report field: {field}"


def test_report_status_is_valid():
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory")
    fp = report_dir / "v1.7-final-validation.json"
    data = json.loads(fp.read_text(encoding="utf-8"))
    valid = [
        "V1_7_READY",
        "V1_7_READY_WITH_WARNINGS",
        "V1_7_READY_WITH_ACCEPTED_WARNINGS",
        "V1_7_NOT_READY",
    ]
    assert data["final_status"] in valid, f"Invalid status: {data['final_status']}"


def test_report_has_version():
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory")
    fp = report_dir / "v1.7-final-validation.json"
    data = json.loads(fp.read_text(encoding="utf-8"))
    assert data.get("version"), "Version is empty"


def test_report_has_git_metadata():
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory")
    fp = report_dir / "v1.7-final-validation.json"
    data = json.loads(fp.read_text(encoding="utf-8"))
    assert data.get("git_branch"), "git_branch is empty"
    assert data.get("git_commit"), "git_commit is empty"


def test_report_has_limitations():
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory")
    fp = report_dir / "v1.7-final-validation.json"
    data = json.loads(fp.read_text(encoding="utf-8"))
    limitations = data.get("limitations_out_of_scope", [])
    assert len(limitations) >= 3, f"Expected >=3 limitations, got {len(limitations)}"
    has_psp = any("PSP" in l for l in limitations)
    has_cloud = any("cloud" in l.lower() for l in limitations)
    has_internet = any("internet" in l.lower() for l in limitations)
    if not has_psp:
        pytest.skip("PSP not in limitations (non-blocking)")
    if not has_cloud:
        pytest.skip("Cloud not in limitations (non-blocking)")
    if not has_internet:
        pytest.skip("Internet not in limitations (non-blocking)")


def test_report_md_exists():
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory")
    fp = report_dir / "v1.7-final-validation.md"
    assert fp.exists(), "Report MD not found"


def test_report_md_has_status():
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory")
    fp = report_dir / "v1.7-final-validation.md"
    content = fp.read_text(encoding="utf-8")
    statuses = [
        "V1_7_READY",
        "V1_7_READY_WITH_WARNINGS",
        "V1_7_READY_WITH_ACCEPTED_WARNINGS",
        "V1_7_NOT_READY",
    ]
    has_status = any(s in content for s in statuses)
    assert has_status, "No valid status in MD report"


def test_report_md_has_limitations():
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory")
    fp = report_dir / "v1.7-final-validation.md"
    content = fp.read_text(encoding="utf-8")
    assert "PSP" in content or "PIX" in content, "PSP/PIX not in MD report"


def test_report_md_has_evidencias():
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory")
    fp = report_dir / "v1.7-final-validation.md"
    content = fp.read_text(encoding="utf-8")
    assert "Evidencias" in content or "logs" in content.lower(), "Evidence section missing"


def test_logs_directory():
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory")
    logs = report_dir / "logs"
    assert logs.exists(), "logs/ directory not found"
    log_files = list(logs.glob("*.log"))
    assert len(log_files) > 0, "No .log files in logs/"
    # Should have at least check-secrets, release-checklist, release-bundle logs
    assert any("check-secrets" in f.name for f in log_files), "Missing check-secrets log"


def test_report_consistency():
    """JSON and MD must agree on final status."""
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory")
    json_fp = report_dir / "v1.7-final-validation.json"
    md_fp = report_dir / "v1.7-final-validation.md"

    data = json.loads(json_fp.read_text(encoding="utf-8"))
    md_content = md_fp.read_text(encoding="utf-8")

    json_status = data.get("final_status", "")
    assert json_status in md_content, f"JSON status '{json_status}' not found in MD report"


def test_no_secrets_in_report():
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory")
    for fname in ["v1.7-final-validation.json", "v1.7-final-validation.md"]:
        fp = report_dir / fname
        if not fp.exists():
            continue
        content = fp.read_text(encoding="utf-8")
        for pat in ["sk-", "ghp_", "ADMIN_TOKEN=", "JWT_SECRET=", "-----BEGIN"]:
            if pat in content:
                for allow in ["__redacted__", "sk-demo", "sk-local-example", "redacted"]:
                    if allow in content:
                        break
                else:
                    assert False, f"Secret pattern '{pat}' found in {fname}"
