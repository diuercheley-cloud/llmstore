import os
import json
import subprocess
from pathlib import Path

def test_security_report_local(tmp_path):
    script_path = Path("scripts/security-report-local.sh")
    assert script_path.exists()
    assert os.access(script_path, os.X_OK)

    # Test --help
    res = subprocess.run([str(script_path), "--help"], capture_output=True, text=True)
    assert "Usage:" in res.stdout

    # Run the report with output to tmp_path
    res = subprocess.run([str(script_path), "--output-dir", str(tmp_path), "--skip-artifacts-scan"], capture_output=True, text=True)
    
    # Even if it fails (due to some actual security issues), it should generate the JSON
    # We find the timestamped dir
    dirs = [d for d in tmp_path.iterdir() if d.is_dir()]
    assert len(dirs) == 1
    report_dir = dirs[0]
    
    json_file = report_dir / "security-report.json"
    md_file = report_dir / "security-report.md"
    
    assert json_file.exists()
    assert md_file.exists()

    with open(json_file) as f:
        data = json.load(f)

    assert "generated_at" in data
    assert "version" in data
    assert "git_branch" in data
    assert "git_commit" in data
    assert "score" in data
    assert data["score"] in ["PASS", "PASS_WITH_WARNINGS", "FAIL"]
    
    assert "totals" in data
    assert "pass" in data["totals"]
    assert "warn" in data["totals"]
    assert "fail" in data["totals"]
    assert "skip" in data["totals"]
    assert "critical_failures" in data["totals"]

    assert "checks" in data
    for check in data["checks"]:
        assert "id" in check
        assert "category" in check
        assert "title" in check
        assert "status" in check
        assert check["status"] in ["pass", "warn", "fail", "skip"]
        assert "severity" in check
        assert check["severity"] in ["critical", "high", "medium", "low"]
        assert "details" in check
        assert "remediation" in check
        assert "evidence" in check

    # Read md
    md_content = md_file.read_text()
    assert "# Security Report" in md_content
    assert data["git_branch"] in md_content
    
    # Ensure no actual secrets are in the output if it passed, but checking strictly for secrets here is hard.
    # Check that check-secrets is referenced in checks
    assert any(c["id"] == "sec-secrets-all" for c in data["checks"])
