import os
import re
import subprocess

import pytest

CONTRACTS_DIR = "contracts"
REQUIRED_TEMPLATES = [
    "SOW_TEMPLATE.md",
    "SERVICE_AGREEMENT_TEMPLATE.md",
    "SUPPORT_TERMS_TEMPLATE.md",
    "ACCEPTANCE_CRITERIA_TEMPLATE.md",
    "README.md",
]

SECRET_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9][a-zA-Z0-9._-]{20,}"),
    re.compile(r"ghp_[a-zA-Z0-9]{36}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"ADMIN_TOKEN=[a-zA-Z0-9._-]{12,}"),
    re.compile(r"JWT_SECRET=[a-zA-Z0-9._-]{12,}"),
    re.compile(r"[a-zA-Z0-9_+.\-]+:[a-zA-Z0-9_+.\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"),
]


@pytest.mark.parametrize("tpl", REQUIRED_TEMPLATES)
def test_template_contains_no_secrets(tpl):
    path = os.path.join(CONTRACTS_DIR, tpl)
    with open(path, "r") as f:
        content = f.read()

    for i, pattern in enumerate(SECRET_PATTERNS):
        matches = pattern.findall(content)
        if matches:
            pytest.fail(
                f"{tpl} contains potential secret matching pattern {i}: {matches[0]}"
            )


@pytest.mark.parametrize("tpl", REQUIRED_TEMPLATES)
def test_template_contains_no_real_emails(tpl):
    path = os.path.join(CONTRACTS_DIR, tpl)
    with open(path, "r") as f:
        content = f.read()

    email_pattern = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
    matches = email_pattern.findall(content)

    allowed = ["e-mail", "email@example.com", "sales@local-ai.solutions"]
    for match in matches:
        if match in allowed or "placeholder" in content.lower():
            continue
        if match == "e-mail" or "[e-mail" in match:
            continue
        pytest.fail(f"{tpl} contains real email address: {match}")


def test_no_env_vars_in_templates():
    for tpl in REQUIRED_TEMPLATES:
        path = os.path.join(CONTRACTS_DIR, tpl)
        with open(path, "r") as f:
            content = f.read()
        env_var_pattern = re.compile(r"\$\{[A-Z_][A-Z0-9_]*\}")
        matches = env_var_pattern.findall(content)
        allowed = ["{DATE}"]
        for match in matches:
            if match in allowed:
                continue
            pytest.fail(f"{tpl} contains environment variable: {match}")


def test_artifacts_contracts_not_tracked():
    result = subprocess.check_output(["git", "ls-files", "artifacts/contracts/"], stderr=subprocess.DEVNULL, text=True)
    assert result.strip() == "", (
        "artifacts/contracts/ should NOT be tracked by Git, but found: "
        + result.strip()
    )
