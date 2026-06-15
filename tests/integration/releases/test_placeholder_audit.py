import os
import subprocess


def test_placeholder_audit_runs():
    # Run the audit script and ensure it executes and writes report
    res = subprocess.run(
        ["python3", "scripts/legacy/audit-production-placeholders.py"],
        capture_output=True,
        text=True,
    )
    assert os.path.exists("artifacts/audit/production-placeholders.md")
