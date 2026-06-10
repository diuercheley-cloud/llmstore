import json
import os
import subprocess
from pathlib import Path

SCRIPT_PATH = Path("scripts/validators/security-report-local.sh")


def test_security_report_local(tmp_path):
    assert SCRIPT_PATH.exists()
    assert os.access(SCRIPT_PATH, os.X_OK)

    res = subprocess.run([str(SCRIPT_PATH), "--help"], capture_output=True, text=True)
    assert "Usage:" in res.stdout

    res = subprocess.run(
        [str(SCRIPT_PATH), "--output-dir", str(tmp_path), "--skip-artifacts-scan"],
        capture_output=True,
        text=True,
    )

    dirs = [entry for entry in tmp_path.iterdir() if entry.is_dir()]
    assert len(dirs) == 1
    report_dir = dirs[0]

    json_file = report_dir / "security-report.json"
    md_file = report_dir / "security-report.md"

    assert json_file.exists()
    assert md_file.exists()

    data = json.loads(json_file.read_text())

    assert "generated_at" in data
    assert "version" in data
    assert "git_branch" in data
    assert "git_commit" in data
    assert data["score"] in {"PASS", "PASS_WITH_WARNINGS", "FAIL"}

    assert set(data["totals"]) >= {"pass", "warn", "fail", "skip", "critical_failures"}
    assert data["checks"]

    for check in data["checks"]:
        assert set(check) >= {
            "id",
            "category",
            "title",
            "status",
            "severity",
            "details",
            "remediation",
            "evidence",
            "meta",
        }
        assert check["status"] in {"pass", "warn", "fail", "skip"}
        assert check["severity"] in {"critical", "high", "medium", "low"}

    md_content = md_file.read_text()
    assert "# Security Report" in md_content
    assert data["git_branch"] in md_content
    assert any(check["id"] == "sec-secrets-all" for check in data["checks"])
