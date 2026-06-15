import subprocess
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


def test_report_json_no_secrets():
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory")
    fp = report_dir / "client-ready-report.json"
    if not fp.exists():
        pytest.skip("Report JSON not found")
    content = fp.read_text(encoding="utf-8")

    secret_patterns = ["sk-", "ghp_", "ADMIN_TOKEN=", "JWT_SECRET=", "-----BEGIN"]
    for pat in secret_patterns:
        if pat in content:
            for allow in ["__redacted__", "sk-demo", "sk-local-example", "redacted"]:
                if allow in content:
                    break
            else:
                assert False, f"Secret pattern '{pat}' found in client-ready-report.json"


def test_report_md_no_secrets():
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory")
    fp = report_dir / "client-ready-report.md"
    if not fp.exists():
        pytest.skip("Report MD not found")
    content = fp.read_text(encoding="utf-8")

    secret_patterns = ["sk-", "ghp_", "ADMIN_TOKEN=", "JWT_SECRET=", "-----BEGIN"]
    for pat in secret_patterns:
        if pat in content:
            for allow in ["__redacted__", "sk-demo", "sk-local-example", "redacted"]:
                if allow in content:
                    break
            else:
                assert False, f"Secret pattern '{pat}' found in client-ready-report.md"


def test_versionable_doc_no_secrets():
    if not VERSIONABLE_DOC.exists():
        pytest.skip("Versionable doc not found")
    content = VERSIONABLE_DOC.read_text(encoding="utf-8")

    secret_patterns = ["sk-", "ghp_", "ADMIN_TOKEN=", "JWT_SECRET=", "-----BEGIN"]
    for pat in secret_patterns:
        if pat in content:
            for allow in ["__redacted__", "sk-demo", "sk-local-example", "redacted"]:
                if allow in content:
                    break
            else:
                assert False, f"Secret pattern '{pat}' found in CLIENT_READY_FINAL_REPORT.md"


def test_check_secrets_passes_on_client_ready_scripts():
    result = subprocess.run(
        [
            "./scripts/validators/check-secrets.sh",
            "--path",
            "scripts/validators/generate-client-ready-report.sh",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"check-secrets on generate-client-ready-report.sh failed:\n"
        f"{result.stdout}\n{result.stderr}"
    )


def test_check_secrets_on_client_ready_docs():
    result = subprocess.run(
        ["./scripts/validators/check-secrets.sh", "--path", "docs/CLIENT_READY_FINAL_REPORT.md"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"check-secrets on CLIENT_READY_FINAL_REPORT.md failed:\n{result.stdout}\n{result.stderr}"
    )


def test_logs_no_secrets():
    report_dir = latest_report_dir()
    if report_dir is None:
        pytest.skip("No report directory")
    logs_dir = report_dir / "logs"
    if not logs_dir.exists():
        pytest.skip("No logs directory")
    for log_file in logs_dir.glob("*"):
        if not log_file.is_file():
            continue
        content = log_file.read_text(encoding="utf-8", errors="replace")
        for pat in ["sk-", "ghp_", "ADMIN_TOKEN="]:
            if pat in content:
                for allow in ["__redacted__", "sk-demo", "sk-local-example"]:
                    if allow in content:
                        break
                else:
                    assert False, f"Secret pattern '{pat}' found in {log_file.name}"


def test_forbidden_files_not_versioned():
    forbidden = [".env.local", ".env", "id_rsa", "credentials.json"]
    for fname in forbidden:
        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", fname],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode != 0, f"Forbidden file '{fname}' is versioned in git"
