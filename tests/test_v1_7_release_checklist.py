import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CHECKLIST_DOC = ROOT / "docs" / "V1_7_RELEASE_CHECKLIST.md"
VALIDATE_SCRIPT = ROOT / "scripts" / "validate-v1.7-release-checklist.sh"

REQUIRED_CATEGORIES = [
    "## 1. Codigo",
    "## 2. Seguranca",
    "## 3. Readiness",
    "## 4. Instalacao",
    "## 5. Backup / Restore",
    "## 6. Upgrade / Rollback",
    "## 7. Demo Comercial",
    "## 8. Documentacao Cliente",
    "## 9. Sales Ops",
    "## 10. Capability Matrix",
    "## 11. Release Artifacts",
    "## 12. Limitacoes Conhecidas",
    "## 13. Go / No-Go",
]


def test_checklist_doc_exists():
    assert CHECKLIST_DOC.exists(), "docs/V1_7_RELEASE_CHECKLIST.md not found"
    assert CHECKLIST_DOC.stat().st_size > 0


def test_validate_script_exists():
    if not VALIDATE_SCRIPT.exists():
        pytest.skip("validate script not found")
    assert os.access(VALIDATE_SCRIPT, os.X_OK), "validate script not executable"


def test_checklist_contains_all_categories():
    content = CHECKLIST_DOC.read_text(encoding="utf-8")
    missing = [c for c in REQUIRED_CATEGORIES if c not in content]
    assert not missing, f"Missing categories: {missing}"


def test_checklist_contains_validation_commands():
    content = CHECKLIST_DOC.read_text(encoding="utf-8")
    cmd_count = content.count("`")
    assert cmd_count >= 20, f"Too few backtick commands: {cmd_count}"


def test_checklist_contains_gonogo():
    content = CHECKLIST_DOC.read_text(encoding="utf-8")
    assert "Go / No-Go" in content or "GO / NO-GO" in content


def test_checklist_has_blocker_flags():
    content = CHECKLIST_DOC.read_text(encoding="utf-8")
    blocker_count = content.count("| true |")
    assert blocker_count >= 10, f"Too few blocker flags: {blocker_count}"


def test_checklist_mentions_psp_pix_out_of_scope():
    content = CHECKLIST_DOC.read_text(encoding="utf-8")
    has_psp = "PSP" in content
    has_pix = "PIX" in content
    assert has_psp or has_pix, "PSP/PIX not mentioned in checklist"


def test_checklist_no_hardcoded_pass_without_evidence():
    content = CHECKLIST_DOC.read_text(encoding="utf-8")
    pass_count = content.count("| pass |")
    fail_count = content.count("| fail |")
    warn_count = content.count("| warn |")
    # Allow pass/fail/warn in Go/No-Go section
    total_status = pass_count + fail_count + warn_count
    assert total_status <= 15, (
        f"Too many hardcoded status values ({total_status}); "
        f"items should start as 'todo'"
    )


def test_checklist_no_secrets():
    content = CHECKLIST_DOC.read_text(encoding="utf-8")
    secret_patterns = ["sk-", "ghp_", "ADMIN_TOKEN=", "JWT_SECRET=", "-----BEGIN"]
    for pat in secret_patterns:
        if pat in content:
            for allow in ["__redacted__", "sk-demo", "sk-local-example", "redacted"]:
                if allow in content:
                    break
            else:
                assert False, f"Secret pattern '{pat}' found in checklist"


def test_validate_script_runs():
    if not VALIDATE_SCRIPT.exists():
        pytest.skip("validate script not found")
    result = subprocess.run(
        ["bash", str(VALIDATE_SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"validate script failed:\n{result.stdout}\n{result.stderr}"


def test_checklist_mentions_no_cloud():
    content = CHECKLIST_DOC.read_text(encoding="utf-8")
    assert "cloud" in content.lower(), "Missing 'cloud' mention in limitations"


def test_checklist_mentions_no_internet():
    content = CHECKLIST_DOC.read_text(encoding="utf-8")
    assert "internet" in content.lower(), "Missing 'internet' mention in limitations"
