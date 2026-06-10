import json
import os
import subprocess
from pathlib import Path

SCRIPT_PATH = Path("scripts/validators/validate-security-cleanup-v1.5.4.sh")


def _write_report(tmp_path: Path, score: str, critical_failures: int, warn: int = 0, fail: int = 0) -> Path:
    report = {
        "score": score,
        "totals": {
            "pass": 1,
            "warn": warn,
            "fail": fail,
            "skip": 0,
            "critical_failures": critical_failures,
        },
        "checks": [],
    }
    report_path = tmp_path / "security-report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    return report_path


def test_validation_script_exists():
    assert SCRIPT_PATH.exists()


def test_validation_script_references_required_commands():
    content = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "./scripts/validators/check-secrets.sh --all" in content
    assert "./scripts/validators/validate-gitignore-security.sh" in content
    assert "./scripts/validators/validate-key-files-local.sh" in content
    assert "./scripts/validators/validate-local-permissions.sh" in content
    assert "./scripts/validators/validate-release-artifacts-security.sh" in content
    assert "./scripts/validators/security-report-local.sh --output-dir artifacts/security-reports" in content


def test_validation_script_accepts_pass_with_warnings(tmp_path):
    report_path = _write_report(tmp_path, score="PASS_WITH_WARNINGS", critical_failures=0, warn=2, fail=0)
    result = subprocess.run(
        ["bash", str(SCRIPT_PATH)],
        env={
            **os.environ,
            "SECURITY_CLEANUP_SKIP_COMMANDS": "1",
            "SECURITY_CLEANUP_REPORT_JSON": str(report_path),
        },
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Score: PASS_WITH_WARNINGS" in result.stdout


def test_validation_script_rejects_fail_score(tmp_path):
    report_path = _write_report(tmp_path, score="FAIL", critical_failures=0, warn=0, fail=1)
    result = subprocess.run(
        ["bash", str(SCRIPT_PATH)],
        env={
            **os.environ,
            "SECURITY_CLEANUP_SKIP_COMMANDS": "1",
            "SECURITY_CLEANUP_REPORT_JSON": str(report_path),
        },
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "score=FAIL" in result.stderr


def test_validation_script_rejects_critical_failures(tmp_path):
    report_path = _write_report(tmp_path, score="PASS_WITH_WARNINGS", critical_failures=1, warn=1, fail=0)
    result = subprocess.run(
        ["bash", str(SCRIPT_PATH)],
        env={
            **os.environ,
            "SECURITY_CLEANUP_SKIP_COMMANDS": "1",
            "SECURITY_CLEANUP_REPORT_JSON": str(report_path),
        },
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "critical_failures=1" in result.stderr
