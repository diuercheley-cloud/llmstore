import os
import re
import subprocess

import pytest

SCRIPT = "scripts/generate-client-monthly-report.sh"


def _extract_path(output: str, suffix: str) -> str | None:
    for line in output.splitlines():
        if ":" in line and suffix in line:
            return line.split(":", 1)[1].strip()
    return None


SECRET_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9][a-zA-Z0-9._-]{20,}"),
    re.compile(r"ghp_[a-zA-Z0-9]{36}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"ADMIN_TOKEN=[a-zA-Z0-9._-]{12,}"),
    re.compile(r"JWT_SECRET=[a-zA-Z0-9._-]{12,}"),
]


def test_report_contains_no_api_keys():
    cmd = [
        "bash", SCRIPT,
        "--email", "nosecrets@example.local",
        "--month", "2026-10",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)

    json_path = _extract_path(result.stdout, "monthly-report.json")
    md_path = _extract_path(result.stdout, "monthly-report.md")

    for filepath in [json_path, md_path]:
        with open(filepath, "r") as f:
            content = f.read()
        for i, pattern in enumerate(SECRET_PATTERNS):
            matches = pattern.findall(content)
            if matches:
                pytest.fail(
                    f"{os.path.basename(filepath)} contains potential secret matching pattern {i}: {matches[0]}"
                )

    os.remove(json_path)
    os.remove(md_path)
    os.rmdir(os.path.dirname(json_path))


def test_report_contains_no_full_prompts():
    cmd = [
        "bash", SCRIPT,
        "--email", "noprompts@example.local",
        "--month", "2026-11",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)

    json_path = _extract_path(result.stdout, "monthly-report.json")
    md_path = _extract_path(result.stdout, "monthly-report.md")

    for filepath in [json_path, md_path]:
        with open(filepath, "r") as f:
            content = f.read().lower()
        # Should not contain raw prompt or RAG content
        sensitive_patterns = [
            "system_prompt",
            "rag_content",
            "raw_prompt",
            "full_prompt",
            "user_message",
            "assistant_message",
        ]
        for pat in sensitive_patterns:
            assert pat not in content, (
                f"{os.path.basename(filepath)} contains sensitive content: {pat}"
            )

    os.remove(json_path)
    os.remove(md_path)
    os.rmdir(os.path.dirname(json_path))


def test_report_contains_no_env_vars():
    cmd = [
        "bash", SCRIPT,
        "--email", "noenv@example.local",
        "--month", "2026-12",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)

    json_path = _extract_path(result.stdout, "monthly-report.json")
    with open(json_path, "r") as f:
        content = f.read()

    env_var_pattern = re.compile(r"\$\{[A-Z_][A-Z0-9_]*\}")
    matches = env_var_pattern.findall(content)
    allowed = []
    for match in matches:
        if match not in allowed:
            pytest.fail(f"JSON contains env var: {match}")

    os.remove(json_path)
    md_path = json_path.replace(".json", ".md")
    if os.path.exists(md_path):
        os.remove(md_path)
    os.rmdir(os.path.dirname(json_path))


def test_artifacts_not_tracked():
    result = os.popen("git ls-files artifacts/monthly-reports/ 2>/dev/null").read()
    assert result.strip() == "", (
        "artifacts/monthly-reports/ should NOT be tracked by Git, but found: "
        + result.strip()
    )
