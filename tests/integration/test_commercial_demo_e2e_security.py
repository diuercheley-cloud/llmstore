import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate-commercial-demo-e2e-local.sh"

# FAKE SECRET FOR TESTS ONLY - do not remove


def test_demo_scripts_have_no_hardcoded_secrets():
    demo_scripts = [
        "scripts/dev/seed-commercial-demo-pack.sh",
        "scripts/dev/reset-commercial-demo-pack.sh",
        "scripts/validators/validate-commercial-demo-pack.sh",
    ]
    for script_path in demo_scripts:
        fp = ROOT / script_path
        if not fp.exists():
            continue
        content = fp.read_text(encoding="utf-8")
        hardcoded = ["sk-", "ghp_", "-----BEGIN PRIVATE KEY-----"]
        for pat in hardcoded:
            if pat in content:
                for allow in ["sk-demo", "sk-local-example", "__redacted__"]:
                    if allow in content:
                        break
                else:
                    assert False, f"{script_path}: hardcoded secret pattern '{pat}'"


def test_fake_data_has_no_real_credentials():
    fake_dir = ROOT / "demo-pack" / "fake-data"
    if not fake_dir.exists():
        pytest.skip("No fake-data directory")
    for f in fake_dir.rglob("*"):
        if f.is_file() and f.suffix in (".json", ".csv", ".txt", ".md"):
            content = f.read_text(encoding="utf-8", errors="ignore")
            for pat in ["sk-", "ghp_", "ADMIN_TOKEN=", "JWT_SECRET="]:
                if pat in content:
                    for allow in ["sk-demo", "sk-local-example", "__redacted__"]:
                        if allow in content:
                            break
                    else:
                        assert False, f"{f}: secret pattern '{pat}' found in fake data"


def test_no_demo_tokens_in_reports():
    report_base = ROOT / "artifacts" / "final-qa" / "commercial-demo-e2e"
    if not report_base.exists():
        pytest.skip("No demo e2e report directory")
    for report_dir in report_base.iterdir():
        if not report_dir.is_dir():
            continue
        for fname in ["demo-e2e-report.json", "demo-e2e-report.md"]:
            fp = report_dir / fname
            if not fp.exists():
                continue
            content = fp.read_text(encoding="utf-8")
            token_patterns = ["sk-", "ghp_", "ADMIN_TOKEN="]
            for pat in token_patterns:
                if pat in content:
                    for allow in ["__redacted__", "sk-demo", "sk-local-example"]:
                        if allow in content:
                            break
                    else:
                        assert False, f"{fname}: token pattern '{pat}' found in report"


def test_check_secrets_script_runs():
    result = subprocess.run(
        ["./scripts/validators/check-secrets.sh", "--all"],
        cwd=ROOT, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, f"check-secrets.sh failed:\n{result.stdout}\n{result.stderr}"


def test_check_secrets_on_demo_pack():
    result = subprocess.run(
        ["./scripts/validators/check-secrets.sh", "--path", "demo-pack"],
        cwd=ROOT, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, f"check-secrets on demo-pack failed:\n{result.stdout}\n{result.stderr}"
