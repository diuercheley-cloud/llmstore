import json
import os
import re
import stat
import subprocess
from pathlib import Path


ALLOWED_SCORES = {"READY", "READY_WITH_WARNINGS", "NOT_READY"}
SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{10,}"),
    re.compile(r"X-Admin-Token:\s*[^\[]", re.IGNORECASE),
    re.compile(r"Authorization:\s*Bearer\s+[^\[]", re.IGNORECASE),
]


def test_production_readiness_script_and_report(tmp_path: Path):
    root_dir = Path(__file__).resolve().parents[1]
    script_path = root_dir / "scripts" / "production-readiness-local.sh"

    assert script_path.exists(), "script does not exist"
    assert os.access(script_path, os.X_OK), "script is not executable"
    mode = script_path.stat().st_mode
    assert mode & stat.S_IXUSR, "owner execute bit is missing"

    help_result = subprocess.run(
        [str(script_path), "--help"],
        capture_output=True,
        text=True,
        cwd=root_dir,
    )
    assert help_result.returncode == 0
    assert "--base-url" in help_result.stdout
    assert "--output-dir" in help_result.stdout
    assert "--json-only" in help_result.stdout
    assert "--strict" in help_result.stdout
    assert "--skip-heavy" in help_result.stdout

    output_root = tmp_path / "production-readiness"
    run_result = subprocess.run(
        [
            str(script_path),
            "--base-url",
            "http://localhost:18080",
            "--output-dir",
            str(output_root),
            "--json-only",
            "--skip-heavy",
        ],
        capture_output=True,
        text=True,
        cwd=root_dir,
    )
    assert run_result.returncode == 0, run_result.stderr

    run_dirs = sorted([item for item in output_root.iterdir() if item.is_dir()])
    assert run_dirs, "no artifact directory was generated"
    latest_dir = run_dirs[-1]
    report_json_path = latest_dir / "report.json"
    report_md_path = latest_dir / "report.md"
    logs_dir = latest_dir / "logs"

    assert report_json_path.exists(), "report.json not found"
    assert report_md_path.exists(), "report.md not found"
    assert logs_dir.is_dir(), "logs directory not found"

    data = json.loads(report_json_path.read_text(encoding="utf-8"))
    required_keys = {
        "generated_at",
        "version",
        "git_branch",
        "git_commit",
        "git_status_clean",
        "base_url",
        "score",
        "totals",
        "checks",
        "artifacts",
    }
    assert required_keys.issubset(data.keys())
    assert data["score"] in ALLOWED_SCORES

    totals = data["totals"]
    for field in ("pass", "warn", "fail", "skip", "critical_failures"):
        assert field in totals
        assert isinstance(totals[field], int)

    checks = data["checks"]
    assert isinstance(checks, list)
    assert checks, "checks list is empty"
    for check in checks:
        for field in ("id", "category", "title", "status", "severity", "details", "remediation", "evidence"):
            assert field in check
        assert check["status"] in {"pass", "warn", "fail", "skip"}
        assert check["severity"] in {"critical", "high", "medium", "low"}

    markdown = report_md_path.read_text(encoding="utf-8")
    assert "# Production Readiness Report Local" in markdown
    assert "PSP real" in markdown
    assert "PIX real" in markdown
    assert "DNS externo" in markdown
    assert "HTTPS obrigatorio" in markdown
    assert "cloud obrigatoria" in markdown

    combined_artifacts = [markdown, report_json_path.read_text(encoding="utf-8")]
    for log_file in logs_dir.glob("*"):
        if log_file.is_file():
            combined_artifacts.append(log_file.read_text(encoding="utf-8", errors="replace"))
    artifact_text = "\n".join(combined_artifacts)
    for pattern in SECRET_PATTERNS:
        assert not pattern.search(artifact_text), f"secret pattern leaked: {pattern.pattern}"

