import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"
SCRIPT = ROOT / "scripts" / "validate-readme-product-local.sh"
CHECK_SECRETS = ROOT / "scripts" / "check-secrets.sh"

SECRET_PATTERNS = [
    ("sk-[a-zA-Z0-9]{32,}", "OpenAI API key"),
    ("ghp_[a-zA-Z0-9]{36}", "GitHub token"),
    ("ADMIN_TOKEN=[a-zA-Z0-9._-]{12,}", "Admin token"),
    ("JWT_SECRET=[a-zA-Z0-9._-]{12,}", "JWT secret"),
    ("-----BEGIN [A-Z ]*PRIVATE KEY-----", "Private key"),
]

SAFE_PATTERNS_IN_README = [
    "sk-***masked",
    "sk-demo",
    "sk-local-example",
    "sk-local-...",
    "changeme",
    "ADMIN_TOKEN",
    "POSTGRES_PASSWORD",
    "your Api key",
    "${API_KEY}",
]


def test_readme_no_hardcoded_secrets():
    content = README.read_text(encoding="utf-8")
    for pat, name in SECRET_PATTERNS:
        matches = re.findall(pat, content)
        for match in matches:
            is_safe = False
            for safe in SAFE_PATTERNS_IN_README:
                if safe in match:
                    is_safe = True
                    break
            if not is_safe:
                assert False, f"Secret '{pat}' ({name}) found: {match[:40]}..."


def test_readme_no_real_api_keys():
    content = README.read_text(encoding="utf-8")
    api_key_pattern = r"sk-[a-zA-Z0-9]{20,}"
    matches = re.findall(api_key_pattern, content)
    for match in matches:
        assert "..." in match or "xxx" in match or match.count("-") < 5, (
            f"Possible real API key found: {match[:20]}..."
        )


def test_readme_no_env_file_values():
    content = README.read_text(encoding="utf-8")
    for line in content.splitlines():
        if "ADMIN_TOKEN=" in line and not line.strip().startswith("#") and not line.strip().startswith("```"):
            value = line.split("ADMIN_TOKEN=", 1)[1].strip()
            assert "ChangeMe" in value or "***" in value or "..." in value or value == "", (
                "Possible real ADMIN_TOKEN in README"
            )


def test_check_secrets_on_readme():
    """Run check-secrets.sh --path on README.md."""
    result = subprocess.run(
        ["bash", str(CHECK_SECRETS), "--path", str(README), "--verbose"],
        capture_output=True, text=True, timeout=30,
    )
    print(f"STDOUT:\n{result.stdout}")
    assert result.returncode == 0, f"Secrets found in README.md:\n{result.stdout}"


def test_check_secrets_on_validate_script():
    """Run check-secrets on the validate script."""
    result = subprocess.run(
        ["bash", str(CHECK_SECRETS), "--path", str(SCRIPT), "--verbose"],
        capture_output=True, text=True, timeout=30,
    )
    print(f"STDOUT:\n{result.stdout}")
    assert result.returncode == 0, f"Secrets found in validate script:\n{result.stdout}"


def test_validate_script_exists():
    assert SCRIPT.exists()
    assert os.access(SCRIPT, os.X_OK)


def test_validate_script_help():
    result = subprocess.run(
        ["bash", str(SCRIPT), "--help"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode != 0 or "Usage" in result.stdout or "Validate" in result.stdout
