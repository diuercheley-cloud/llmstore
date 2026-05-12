import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
AUDIT_SCRIPT = ROOT / "scripts" / "audit-v1.6-release-line.sh"
VALIDATE_SCRIPT = ROOT / "scripts" / "validate-v1.6-release-line-audit.sh"
AUDIT_SUMMARY_DOC = ROOT / "docs" / "V1_6_AUDIT_SUMMARY.md"
AUDIT_ARTIFACTS_BASE = ROOT / "artifacts" / "final-qa" / "v1.6-audit"

REQUIRED_VERSIONS = [
    "v1.6.0-openai-compat",
    "v1.6.1-openai-compat",
    "v1.6.1-product-hardening",
    "v1.6.2-installer-polish",
    "v1.6.3-readiness-cleanup",
    "v1.6.4-customer-demo-pack",
    "v1.6.5-sales-ops",
    "v1.6.6-repo-cleanup",
]

REQUIRED_RELEASE_FILES = [
    "release-manifest.json",
    "summary.json",
    "summary.md",
    "bundle-manifest.json",
    "bundle-checksums.sha256",
]


def test_audit_script_exists():
    assert AUDIT_SCRIPT.exists(), "scripts/audit-v1.6-release-line.sh missing"
    assert os.access(AUDIT_SCRIPT, os.X_OK), "audit script not executable"


def test_validate_script_exists():
    assert VALIDATE_SCRIPT.exists(), "scripts/validate-v1.6-release-line-audit.sh missing"
    assert os.access(VALIDATE_SCRIPT, os.X_OK), "validate script not executable"


def test_audit_summary_doc_exists():
    assert AUDIT_SUMMARY_DOC.exists(), "docs/V1_6_AUDIT_SUMMARY.md missing"


def test_audit_summary_contains_all_versions():
    content = AUDIT_SUMMARY_DOC.read_text(encoding="utf-8")
    missing = [v for v in REQUIRED_VERSIONS if v not in content]
    assert not missing, f"Versions missing from audit summary: {missing}"


def test_audit_script_runs_and_produces_json():
    result = subprocess.run(
        ["bash", str(AUDIT_SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, f"Audit script failed:\n{result.stderr}"

    latest = latest_audit_dir()
    assert latest is not None, "No audit output directory created"
    audit_json = latest / "v1.6-audit.json"
    assert audit_json.exists(), "v1.6-audit.json not produced"
    assert audit_json.stat().st_size > 0, "v1.6-audit.json is empty"


def test_audit_json_is_valid():
    latest = latest_audit_dir()
    if latest is None:
        pytest.skip("No audit output directory found")

    audit_json = latest / "v1.6-audit.json"
    data = json.loads(audit_json.read_text(encoding="utf-8"))

    assert "audit_metadata" in data, "Missing audit_metadata"
    assert "versions" in data, "Missing versions array"
    assert "summary" in data, "Missing summary"

    assert len(data["versions"]) >= len(REQUIRED_VERSIONS), (
        f"Expected at least {len(REQUIRED_VERSIONS)} versions, got {len(data['versions'])}"
    )

    audited_tags = {v["version"] for v in data["versions"]}
    missing = set(REQUIRED_VERSIONS) - audited_tags
    assert not missing, f"Versions not audited: {missing}"


def test_audit_summary_has_no_inconsistencies_unknown():
    latest = latest_audit_dir()
    if latest is None:
        pytest.skip("No audit output directory found")

    audit_json = latest / "v1.6-audit.json"
    data = json.loads(audit_json.read_text(encoding="utf-8"))

    for v in data["versions"]:
        assert v["tag_commit"] != "UNRESOLVED", f"{v['version']}: tag commit unresolved"
        if v["tag_stable_consistent"] == "unknown":
            assert False, f"{v['version']}: tag/stable consistency unknown"


def test_audit_md_exists():
    latest = latest_audit_dir()
    if latest is None:
        pytest.skip("No audit output directory found")

    audit_md = latest / "v1.6-audit.md"
    assert audit_md.exists(), "v1.6-audit.md not produced"
    assert audit_md.stat().st_size > 0, "v1.6-audit.md is empty"


def test_validate_script_execution():
    result = subprocess.run(
        ["bash", str(VALIDATE_SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, (
        f"Validate script failed (exit {result.returncode}):\n{result.stdout}\n{result.stderr}"
    )


def latest_audit_dir():
    if not AUDIT_ARTIFACTS_BASE.exists():
        return None
    subdirs = sorted([d for d in AUDIT_ARTIFACTS_BASE.iterdir() if d.is_dir()])
    return subdirs[-1] if subdirs else None
