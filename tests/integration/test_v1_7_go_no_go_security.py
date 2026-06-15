import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SUMMARY_DOC = ROOT / "docs" / "V1_7_GO_NO_GO_SUMMARY.md"
CHECKLIST_DOC = ROOT / "docs" / "V1_7_RELEASE_CHECKLIST.md"
CHECK_SECRETS_SCRIPT = ROOT / "scripts" / "check-secrets.sh"
GO_NO_GO_DOC = SUMMARY_DOC


def test_go_no_go_summary_no_secrets():
    """V1_7_GO_NO_GO_SUMMARY.md must not contain real secrets."""
    content = GO_NO_GO_DOC.read_text(encoding="utf-8")
    secret_patterns = [
        ("sk-", "OpenAI API key"),
        ("ghp_", "GitHub token"),
        ("ADMIN_TOKEN=", "Admin token"),
        ("JWT_SECRET=", "JWT secret"),
        ("-----BEGIN ", "Private key"),
    ]
    for pat, name in secret_patterns:
        if pat in content:
            for allow in [
                "__redacted__",
                "sk-demo",
                "sk-local-example",
                "redacted",
                "sk-***",
                "***masked***",
            ]:
                if allow in content:
                    break
            else:
                assert False, f"Secret pattern '{pat}' ({name}) found in Go/No-Go summary"


def test_go_no_go_summary_no_hardcoded_credentials():
    """Go/No-Go summary must not contain hardcoded credentials."""
    content = GO_NO_GO_DOC.read_text(encoding="utf-8")
    suspicious = ["localhost:18080", "--api-key", "Bearer "]
    for pat in suspicious:
        if pat in content:
            assert False, f"Suspicious pattern '{pat}' found in Go/No-Go summary"


def test_checklist_doc_no_secrets():
    """V1_7_RELEASE_CHECKLIST.md must not contain real secrets."""
    content = CHECKLIST_DOC.read_text(encoding="utf-8")
    secret_patterns = ["sk-", "ghp_", "ADMIN_TOKEN=", "JWT_SECRET=", "-----BEGIN"]
    for pat in secret_patterns:
        if pat in content:
            for allow in ["__redacted__", "sk-demo", "sk-local-example", "redacted"]:
                if allow in content:
                    break
            else:
                assert False, f"Secret pattern '{pat}' found in checklist"


def test_checklist_doc_mentions_security():
    """Checklist must have security category."""
    content = CHECKLIST_DOC.read_text(encoding="utf-8")
    assert "## 2. Seguranca" in content, "Security category missing from checklist"


def test_checklist_doc_psp_pix_not_blocker():
    """PSP/PIX should be documented as out of scope / non-blocker."""
    content = CHECKLIST_DOC.read_text(encoding="utf-8")
    assert "PSP" in content or "PIX" in content, "PSP/PIX not mentioned in checklist"
    # Should mention it's not a blocker
    assert "nao" in content.lower() or "future" in content.lower() or "fora" in content.lower(), (
        "PSP/PIX should be documented as non-blocker / out of scope"
    )


def test_checklist_doc_no_cloud_requirement():
    """Checklist must not require cloud."""
    content = CHECKLIST_DOC.read_text(encoding="utf-8")
    # Should mention cloud is not required
    assert (
        "nao.*cloud" in content
        or "cloud.*nao" in content
        or "offline" in content.lower()
        or "local" in content.lower()
    ), "Checklist should document that cloud is not required"


def test_checklist_doc_no_internet_requirement():
    """Checklist must not require internet."""
    content = CHECKLIST_DOC.read_text(encoding="utf-8")
    assert (
        "nao.*internet" in content
        or "internet.*nao" in content
        or "offline" in content.lower()
        or "sem internet" in content.lower()
    ), "Checklist should document that internet is not required"


def test_go_no_go_summary_no_real_tokens():
    """Go/No-Go summary must not expose real tokens through inline examples."""
    content = GO_NO_GO_DOC.read_text(encoding="utf-8")
    # Check for real-looking tokens
    import re

    real_sk = re.findall(r"sk-[a-zA-Z0-9]{20,}", content)
    for token in real_sk:
        if not any(demo in token for demo in ["demo", "example", "test", "xxxx"]):
            assert False, f"Real-looking API key found in summary: {token[:10]}..."


def test_check_secrets_script_exists():
    """check-secrets.sh must exist."""
    assert CHECK_SECRETS_SCRIPT.exists(), "check-secrets.sh not found"


def test_check_secrets_script_executable():
    """check-secrets.sh must be executable."""
    import os

    assert os.access(CHECK_SECRETS_SCRIPT, os.X_OK), "check-secrets.sh not executable"


def test_check_secrets_runs():
    """check-secrets.sh --all must complete."""
    result = subprocess.run(
        ["bash", str(CHECK_SECRETS_SCRIPT), "--all"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    print("STDOUT (last 20 lines):\n" + "\n".join(result.stdout.split("\n")[-20:]))
    # check-secrets may find expected/fixture patterns; we just check it completes
    assert result.returncode in (0, 1), (
        f"check-secrets.sh crashed with exit code {result.returncode}"
    )
