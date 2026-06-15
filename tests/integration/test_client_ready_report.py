import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
REPORT_BASE = ROOT / "artifacts" / "final-qa" / "client-ready"
VERSIONABLE_DOC = ROOT / "docs" / "CLIENT_READY_FINAL_REPORT.md"


def latest_report_dir():
    if not REPORT_BASE.exists():
        return None
    subdirs = sorted([d for d in REPORT_BASE.iterdir() if d.is_dir()])
    return subdirs[-1] if subdirs else None


def test_report_json_exists():
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory (run generate-client-ready-report.sh first)")
    report_json = report_dir / "client-ready-report.json"
    assert report_json.exists(), "client-ready-report.json not found"
    assert report_json.stat().st_size > 0


def test_report_md_exists():
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory")
    report_md = report_dir / "client-ready-report.md"
    assert report_md.exists(), "client-ready-report.md not found"
    assert report_md.stat().st_size > 0


def test_versionable_doc_exists():
    assert VERSIONABLE_DOC.exists(), "docs/CLIENT_READY_FINAL_REPORT.md not found"
    assert VERSIONABLE_DOC.stat().st_size > 0


def test_report_is_valid_json():
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory")
    report_json = report_dir / "client-ready-report.json"
    data = json.loads(report_json.read_text(encoding="utf-8"))

    required = [
        "report_type",
        "generated_at",
        "version",
        "git_branch",
        "git_commit",
        "final_status",
        "evaluation_criteria",
        "summary",
        "known_limitations",
        "residual_risks",
        "v1_7_recommendation",
    ]
    for field in required:
        assert field in data, f"Missing required field: {field}"

    assert data["report_type"] == "client_ready_report"
    assert data["final_status"] in ("CLIENT_READY", "CLIENT_READY_WITH_WARNINGS", "NOT_READY")


def test_report_has_evaluation_criteria():
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory")
    report_json = report_dir / "client-ready-report.json"
    data = json.loads(report_json.read_text(encoding="utf-8"))

    criteria = data.get("evaluation_criteria", [])
    assert len(criteria) >= 8, f"Expected >=8 criteria, got {len(criteria)}"

    criterion_ids = [c.get("id") for c in criteria]
    for cid in [
        "security_report",
        "production_readiness",
        "validate_local_production",
        "clean_install",
        "restore_rollback",
        "commercial_demo_e2e",
        "secrets_check",
        "forbidden_files",
        "release_metadata",
    ]:
        assert cid in criterion_ids, f"Missing criterion: {cid}"


def test_report_has_known_limitations():
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory")
    report_json = report_dir / "client-ready-report.json"
    data = json.loads(report_json.read_text(encoding="utf-8"))

    limitations = data.get("known_limitations", [])
    assert len(limitations) > 0, "No known limitations listed"
    assert any("PSP" in l for l in limitations), "Missing PSP limitation"
    assert any("PIX" in l for l in limitations), "Missing PIX limitation"


def test_report_has_v1_7_recommendation():
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory")
    report_json = report_dir / "client-ready-report.json"
    data = json.loads(report_json.read_text(encoding="utf-8"))

    rec = data.get("v1_7_recommendation", "")
    assert len(rec) > 0, "Empty v1.7.0 recommendation"
    assert "v1.7.0" in rec, "Missing v1.7.0 reference"


def test_report_has_logs_dir():
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory")
    logs_dir = report_dir / "logs"
    assert logs_dir.exists(), "logs/ directory not found"
    assert logs_dir.is_dir()


def test_report_mentions_readiness_and_security():
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory")
    report_json = report_dir / "client-ready-report.json"
    data = json.loads(report_json.read_text(encoding="utf-8"))

    text = json.dumps(data).lower()
    assert "security" in text, "Missing security mention"
    assert "readiness" in text, "Missing readiness mention"


def test_versionable_doc_has_checklist():
    if not VERSIONABLE_DOC.exists():
        pytest.skip("Versionable doc not found")
    content = VERSIONABLE_DOC.read_text(encoding="utf-8")
    assert "Checklist Final" in content or "checklist" in content.lower()
