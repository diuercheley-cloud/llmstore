import os
import subprocess

import pytest


def test_diagnostic_file_exists():
    assert os.path.exists("docs/SECURITY_CLEANUP_v1.5.4.md")


def test_diagnostic_file_no_secrets():
    with open("docs/SECURITY_CLEANUP_v1.5.4.md") as f:
        content = f.read()
        # Basic checks for common secret patterns
        assert "ADMIN_TOKEN=917b7930" not in content
        assert "ADMIN_TOKEN=change-this" not in content
        # Ensure it contains masked markers if evidence was present
        assert "..." in content or "[MASKED]" in content or "..." in content


def test_parser_script_exists_and_executable():
    assert os.path.exists("scripts/validators/parse-security-report-local.sh")
    assert os.access("scripts/validators/parse-security-report-local.sh", os.X_OK)


def test_parser_output_masking():
    # Find a report to test with
    reports_dir = "artifacts/security-reports"
    if not os.path.exists(reports_dir):
        pytest.skip("No security reports found to test parser")

    subdirs = sorted(os.listdir(reports_dir), reverse=True)
    if not subdirs:
        pytest.skip("No security reports found to test parser")

    report_json = os.path.join(reports_dir, subdirs[0], "security-report.json")

    result = subprocess.run(
        ["./scripts/validators/parse-security-report-local.sh", report_json],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    output = result.stdout

    # Check that common secret patterns are NOT in output
    assert "ADMIN_TOKEN=917b7930" not in output
    assert "ADMIN_TOKEN=change-this" not in output

    # Check for summary info
    assert "Score:" in output
    assert "Totals:" in output


def test_diagnostic_mentions_status():
    with open("docs/SECURITY_CLEANUP_v1.5.4.md") as f:
        content = f.read()
        assert "PASS_WITH_WARNINGS" in content or "PASS" in content or "FAIL" in content
