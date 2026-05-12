import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SUMMARY_DOC = ROOT / "docs" / "V1_7_GO_NO_GO_SUMMARY.md"
VALIDATE_SCRIPT = ROOT / "scripts" / "validate-v1.7-go-no-go-summary.sh"


def test_summary_doc_exists():
    assert SUMMARY_DOC.exists(), "docs/V1_7_GO_NO_GO_SUMMARY.md not found"
    assert SUMMARY_DOC.stat().st_size > 0


def test_validate_script_exists():
    assert VALIDATE_SCRIPT.exists(), "validate-v1.7-go-no-go-summary.sh not found"
    assert os.access(VALIDATE_SCRIPT, os.X_OK), "validate script not executable"


def test_summary_has_valid_status():
    content = SUMMARY_DOC.read_text(encoding="utf-8")
    valid_statuses = ["GO", "GO_WITH_WARNINGS", "NO_GO"]
    has_status = any(s in content for s in valid_statuses)
    assert has_status, f"No valid status found in summary. Expected one of: {valid_statuses}"
    # Check status appears in bold in first 20 lines
    first_block = "\n".join(content.split("\n")[:20])
    status_found = False
    for s in valid_statuses:
        if f"**{s}**" in first_block:
            status_found = True
            break
    assert status_found, "Status not found as bold header in summary"


def test_summary_has_version():
    content = SUMMARY_DOC.read_text(encoding="utf-8")
    assert "v1.7.0" in content, "Version v1.7.0 not mentioned in summary"


def test_summary_mentions_psp_pix():
    content = SUMMARY_DOC.read_text(encoding="utf-8")
    assert "PSP" in content or "PIX" in content, (
        "PSP/PIX not mentioned in summary as out of scope"
    )


def test_summary_mentions_blockers():
    content = SUMMARY_DOC.read_text(encoding="utf-8")
    assert "Blockers" in content or "blockers" in content.lower(), (
        "Blockers section not found in summary"
    )


def test_summary_mentions_warnings():
    content = SUMMARY_DOC.read_text(encoding="utf-8")
    assert "Warnings" in content or "warnings" in content.lower(), (
        "Warnings section not found in summary"
    )


def test_summary_has_evidence():
    content = SUMMARY_DOC.read_text(encoding="utf-8")
    markers = ["Evidencias", "Security", "Secrets", "Readiness"]
    found = [m for m in markers if m in content]
    assert len(found) >= 2, (
        f"Too few evidence markers found: {found}. Expected at least 2 of {markers}"
    )


def test_summary_has_limitations():
    content = SUMMARY_DOC.read_text(encoding="utf-8")
    assert "Limitacoes Fora do Escopo" in content, (
        "Limitacoes Fora do Escopo section not found"
    )


def test_summary_has_final_recommendation():
    content = SUMMARY_DOC.read_text(encoding="utf-8")
    assert "Recomendacao Final" in content, (
        "Recomendacao Final section not found"
    )


def test_summary_has_commands():
    content = SUMMARY_DOC.read_text(encoding="utf-8")
    assert "Comandos Executados" in content or "run-v1.7-release-checklist" in content, (
        "Comandos Executados section not found"
    )


def test_summary_no_secrets():
    content = SUMMARY_DOC.read_text(encoding="utf-8")
    secret_patterns = ["sk-", "ghp_", "ADMIN_TOKEN=", "JWT_SECRET=", "-----BEGIN"]
    for pat in secret_patterns:
        if pat in content:
            for allow in ["__redacted__", "sk-demo", "sk-local-example", "redacted", "sk-***"]:
                if allow in content:
                    break
            else:
                assert False, f"Secret pattern '{pat}' found in summary"


def test_summary_contains_cloud_offline_note():
    content = SUMMARY_DOC.read_text(encoding="utf-8")
    assert "cloud" in content.lower() or "offline" in content.lower(), (
        "Cloud/offline note not found in summary"
    )


def test_summary_contains_internet_offline_note():
    content = SUMMARY_DOC.read_text(encoding="utf-8")
    assert "internet" in content.lower() or "offline" in content.lower(), (
        "Internet/offline note not found in summary"
    )


def test_validate_script_runs():
    result = subprocess.run(
        ["bash", str(VALIDATE_SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    print(f"STDOUT:\n{result.stdout}")
    print(f"STDERR:\n{result.stderr}")
    assert result.returncode == 0, (
        f"Validate script failed:\n{result.stdout}\n{result.stderr}"
    )


def test_summary_not_go_with_blockers():
    """Ensure summary doesn't mark GO if latest artifact has blocker fails."""
    content = SUMMARY_DOC.read_text(encoding="utf-8")

    # Find latest artifact
    artifacts_base = ROOT / "artifacts" / "v1.7-release-checklist"
    latest_artifact = None
    if artifacts_base.exists():
        subdirs = sorted([d for d in artifacts_base.iterdir() if d.is_dir()])
        if subdirs:
            candidate = subdirs[-1] / "v1.7-checklist-status.json"
            if candidate.exists():
                latest_artifact = candidate

    if latest_artifact is None:
        pytest.skip("No artifact found to cross-check")

    import json
    data = json.loads(latest_artifact.read_text(encoding="utf-8"))
    bf = data.get("blocker_fails", 0)

    if bf > 0:
        assert "NO_GO" in content, (
            f"Artifact has {bf} blocker fails but summary does not indicate NO_GO"
        )


def test_summary_has_remediation():
    content = SUMMARY_DOC.read_text(encoding="utf-8")
    has_remediation = "Remediacao" in content or "Pos-Release" in content or "recomendac" in content.lower()
    if has_remediation:
        return
    pytest.skip("No remediation/pos-release section found (non-blocking)")
