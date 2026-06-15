import json
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
E2E_SCRIPT = ROOT / "scripts" / "validate-hybrid-platform-e2e-local.sh"
REPORT_SCRIPT = ROOT / "scripts" / "validate-hybrid-platform-report.sh"
ARTIFACTS_DIR = ROOT / "artifacts" / "hybrid-platform-e2e"

SECRET_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"ghp_[a-zA-Z0-9]{36}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]

SAFE_TOKENS = [
    "sk-example",
    "sk-demo",
    "sk-test",
    "test-admin-token",
    "admin-token-example",
    "sk-local-example",
    "sk-demo-example",
    "sk-demo-xxxx",
    "your-api-key",
    "changeme",
]


def _has_real_secret(text: str) -> list[str]:
    findings = []
    for pattern in SECRET_PATTERNS:
        matches = pattern.findall(text)
        for match in matches:
            is_safe = any(safe in match for safe in SAFE_TOKENS)
            if not is_safe and len(match) >= 10:
                findings.append(match)
    return findings


class TestHybridPlatformSecurity:
    def test_e2e_script_no_secrets(self):
        """The E2E validation script itself should not contain real secrets."""
        content = E2E_SCRIPT.read_text()
        findings = _has_real_secret(content)
        assert len(findings) == 0, f"E2E script contains potential secrets: {findings}"

    def test_report_script_no_secrets(self):
        """The report validation script should not contain real secrets."""
        content = REPORT_SCRIPT.read_text()
        findings = _has_real_secret(content)
        assert len(findings) == 0, f"Report script contains potential secrets: {findings}"

    def test_e2e_script_no_api_key_hardcoding(self):
        """E2E script should not hardcode real API keys."""
        content = E2E_SCRIPT.read_text()
        # Look for patterns like API_KEY= or api_key = but skip env var patterns
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if re.search(
                r'(api_key|API_KEY|apikey|api-key)\s*[=:]\s*["\']?(sk-[a-zA-Z0-9])',
                stripped,
            ):
                is_safe = any(safe in stripped.lower() for safe in SAFE_TOKENS)
                if not is_safe:
                    pytest.fail(f"Line {i}: Potentially hardcoded API key: {stripped[:100]}")

    def test_e2e_script_admin_token_not_hardcoded(self):
        """E2E script should not hardcode admin tokens (use test token or env)."""
        content = E2E_SCRIPT.read_text()
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if re.search(
                r'(admin.?token|ADMIN_TOKEN)\s*[=:]\s*["\']?[a-zA-Z0-9_]{12,}',
                stripped,
            ):
                if "test-admin-token" not in stripped and "admin-token-example" not in stripped:
                    pytest.fail(f"Line {i}: Potentially hardcoded admin token: {stripped[:100]}")

    def test_e2e_script_no_sk_pattern_leaks(self):
        """Check that the script doesn't accidentally leak 'sk-' patterns in output."""
        content = E2E_SCRIPT.read_text()
        findings = re.findall(r'"sk-[a-zA-Z0-9]+"', content)
        dangerous = [f for f in findings if not any(safe in f for safe in SAFE_TOKENS)]
        assert len(dangerous) == 0, f"Script contains potentially leaked sk- patterns: {dangerous}"

    def test_artifacts_no_secrets(self):
        """Generated artifact JSON reports should not contain secrets."""
        if not ARTIFACTS_DIR.exists():
            pytest.skip("No hybrid-platform-e2e artifacts directory found")
        dirs = sorted(ARTIFACTS_DIR.iterdir())
        if not dirs:
            pytest.skip("No report subdirectories found")
        latest = dirs[-1]
        report_json = latest / "hybrid-e2e.json"
        report_md = latest / "hybrid-e2e.md"

        for report_path in [report_json, report_md]:
            if not report_path.exists():
                continue
            content = report_path.read_text()
            findings = _has_real_secret(content)
            assert len(findings) == 0, f"{report_path.name} contains potential secrets: {findings}"

    def test_artifacts_no_bearer_token_leak(self):
        """Check that 'Bearer' in artifacts only has masked tokens."""
        if not ARTIFACTS_DIR.exists():
            pytest.skip("No artifacts directory")
        dirs = sorted(ARTIFACTS_DIR.iterdir())
        if not dirs:
            pytest.skip("No report subdirectories")
        latest = dirs[-1]
        for fname in ["hybrid-e2e.json", "hybrid-e2e.md"]:
            report_path = latest / fname
            if not report_path.exists():
                continue
            content = report_path.read_text()
            bearer_matches = re.findall(r"Bearer\s+([a-zA-Z0-9._-]{10,})", content)
            for match in bearer_matches:
                if match in SAFE_TOKENS:
                    continue
                # Check if it's a masked token
                if "masked" in match.lower() or "redacted" in match.lower():
                    continue
                pytest.fail(f"{fname}: Possible Bearer token leak: 'Bearer {match[:20]}...'")

    def test_check_secrets_all_passes(self):
        """check-secrets --all should pass for the scripts."""
        result = subprocess.run(
            ["bash", str(ROOT / "scripts" / "check-secrets.sh"), "--all"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            # Show only the last 30 lines of output for debugging
            output_lines = result.stdout.strip().split("\n")
            last_lines = "\n".join(output_lines[-30:])
            pytest.fail(f"check-secrets --all failed (exit {result.returncode}):\n{last_lines}")

    def test_e2e_script_uses_env_vars_not_hardcoded_creds(self):
        """E2E script should use env vars for credentials."""
        content = E2E_SCRIPT.read_text()
        # Should reference os.environ or $VAR for sensitive values
        assert "os.environ" in content or "\\${" in content or "${" in content, (
            "Script should use environment variables for configuration"
        )

    def test_logs_no_secrets(self):
        """Generated log files should not contain secrets."""
        if not ARTIFACTS_DIR.exists():
            pytest.skip("No artifacts directory")
        dirs = sorted(ARTIFACTS_DIR.iterdir())
        if not dirs:
            pytest.skip("No report subdirectories")
        latest = dirs[-1]
        logs_dir = latest / "logs"
        if not logs_dir.exists():
            pytest.skip("No logs directory")
        for log_file in logs_dir.iterdir():
            if log_file.is_file():
                content = log_file.read_text(errors="ignore")
                findings = _has_real_secret(content)
                assert len(findings) == 0, f"{log_file.name} contains potential secrets: {findings}"

    def test_security_report_from_e2e_is_pass(self):
        """The security report generated during E2E should be PASS."""
        sec_reports_dir = ROOT / "artifacts" / "security-reports"
        if not sec_reports_dir.exists():
            pytest.skip("No security-reports artifacts directory found")
        dirs = sorted(sec_reports_dir.iterdir())
        if not dirs:
            pytest.skip("No security report subdirectories")
        latest = dirs[-1]
        report_json = latest / "security-report.json"
        if not report_json.exists():
            pytest.skip("No security-report.json found")
        with open(report_json) as f:
            data = json.load(f)
        score = data.get("score", "")
        assert score in ("PASS", "PASS_WITH_WARNINGS"), (
            f"Security report score should be PASS, got: {score}"
        )

    def test_security_report_score_not_fail(self):
        """Security report must not be FAIL."""
        sec_reports_dir = ROOT / "artifacts" / "security-reports"
        if not sec_reports_dir.exists():
            pytest.skip("No security-reports artifacts directory found")
        dirs = sorted(sec_reports_dir.iterdir())
        if not dirs:
            pytest.skip("No security report subdirectories")
        latest = dirs[-1]
        report_json = latest / "security-report.json"
        if not report_json.exists():
            pytest.skip("No security-report.json found")
        with open(report_json) as f:
            data = json.load(f)
        score = data.get("score", "")
        assert score != "FAIL", "Security report must not be FAIL"
