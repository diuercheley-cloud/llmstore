import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
REPORT_BASE = ROOT / "artifacts" / "final-qa" / "client-ready"
VERSIONABLE_DOC = ROOT / "docs" / "CLIENT_READY_FINAL_REPORT.md"


ALLOWED_STATUSES = {"CLIENT_READY", "CLIENT_READY_WITH_WARNINGS", "NOT_READY"}


def latest_report_dir():
    if not REPORT_BASE.exists():
        return None
    subdirs = sorted([d for d in REPORT_BASE.iterdir() if d.is_dir()])
    return subdirs[-1] if subdirs else None


def test_final_status_is_valid():
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory")
    report_json = report_dir / "client-ready-report.json"
    data = json.loads(report_json.read_text(encoding="utf-8"))
    assert data["final_status"] in ALLOWED_STATUSES, (
        f"Invalid status: {data['final_status']}"
    )


def test_report_version_matches_repo():
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory")
    actual_version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    report_json = report_dir / "client-ready-report.json"
    data = json.loads(report_json.read_text(encoding="utf-8"))
    assert data["version"] == actual_version, (
        f"Report version '{data['version']}' != repo version '{actual_version}'"
    )


def test_versionable_doc_status_matches_report():
    report_dir = latest_report_dir()
    if report_dir is None or not VERSIONABLE_DOC.exists():
        pytest.skip("Report or versionable doc not found")
    report_json = report_dir / "client-ready-report.json"
    data = json.loads(report_json.read_text(encoding="utf-8"))
    doc_content = VERSIONABLE_DOC.read_text(encoding="utf-8")
    status_from_report = data["final_status"]
    assert status_from_report in doc_content, (
        f"Status '{status_from_report}' not found in versionable doc"
    )


def test_versionable_doc_has_general_status():
    if not VERSIONABLE_DOC.exists():
        pytest.skip("Versionable doc not found")
    content = VERSIONABLE_DOC.read_text(encoding="utf-8")
    has_status = any(s in content for s in ALLOWED_STATUSES)
    assert has_status, "Versionable doc missing general status"


def test_versionable_doc_has_recommendation():
    if not VERSIONABLE_DOC.exists():
        pytest.skip("Versionable doc not found")
    content = VERSIONABLE_DOC.read_text(encoding="utf-8")
    assert "v1.7.0" in content, "Missing v1.7.0 recommendation"
    assert "Recomendacao" in content or "recomendacao" in content.lower(), (
        "Missing recommendation section"
    )


def test_versionable_doc_has_limitations():
    if not VERSIONABLE_DOC.exists():
        pytest.skip("Versionable doc not found")
    content = VERSIONABLE_DOC.read_text(encoding="utf-8")
    assert "PSP" in content or "PIX" in content, "Missing PSP/PIX limitation"
    assert "Limitacoes" in content or "limita" in content.lower(), (
        "Missing limitations section"
    )


def test_versionable_doc_has_risks():
    if not VERSIONABLE_DOC.exists():
        pytest.skip("Versionable doc not found")
    content = VERSIONABLE_DOC.read_text(encoding="utf-8")
    assert "Riscos" in content or "riscos" in content.lower(), (
        "Missing residual risks section"
    )


def test_report_summary_consistency():
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory")
    report_json = report_dir / "client-ready-report.json"
    data = json.loads(report_json.read_text(encoding="utf-8"))
    summary = data.get("summary", {})
    assert "security_score" in summary
    assert "readiness_score" in summary
    assert "validation_success" in summary
    assert "demo_e2e_status" in summary
    assert "secrets_clean" in summary
    assert "forbidden_files_clean" in summary
    assert "release_metadata_ok" in summary


def test_versionable_doc_checklist_items():
    if not VERSIONABLE_DOC.exists():
        pytest.skip("Versionable doc not found")
    content = VERSIONABLE_DOC.read_text(encoding="utf-8")
    checklist_items = [
        "Security report",
        "readiness",
        "Validate local production",
        "Clean install",
        "Restore",
        "Demo",
        "secrets",
        "forbidden",
        "Release metadata",
    ]
    for item in checklist_items:
        assert item.lower() in content.lower(), f"Checklist item '{item}' not found"
