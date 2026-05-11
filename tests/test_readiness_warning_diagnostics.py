import os
import json
import subprocess
import pytest
from pathlib import Path

def test_diagnose_script_exists_and_executable():
    script_path = Path("scripts/diagnose-readiness-warnings-local.sh")
    assert script_path.exists()
    assert os.access(script_path, os.X_OK)

def test_report_parser_with_fake_json(tmp_path):
    # Setup fake report
    report_json = tmp_path / "report.json"
    
    fake_data = {
        "score": "READY_WITH_WARNINGS",
        "checks": [
            {
                "id": "saas_rate_limit",
                "status": "warn",
                "details": "teste de rate limit falhou",
                "severity": "high"
            },
            {
                "id": "git_status_clean",
                "status": "warn",
                "details": "worktree dirty",
                "severity": "medium"
            }
        ]
    }
    report_json.write_text(json.dumps(fake_data))
    
    # Run diagnostics script pointing to this fake report
    res = subprocess.run(
        ["bash", "scripts/diagnose-readiness-warnings-local.sh", str(report_json)],
        capture_output=True,
        text=True
    )
    
    assert res.returncode == 0
    assert "[WARN] ID: saas_rate_limit" in res.stdout
    assert "Categoria: probe_bug" in res.stdout
    assert "[WARN] ID: git_status_clean" in res.stdout
    assert "Categoria: environment_state" in res.stdout

def test_readiness_cleanup_doc_exists():
    assert Path("docs/READINESS_CLEANUP_v1.6.3.md").exists()

def test_no_secrets_in_output():
    # Run the diagnostics script and check for things that look like secrets
    res = subprocess.run(
        ["./scripts/diagnose-readiness-warnings-local.sh"],
        capture_output=True,
        text=True
    )
    output = res.stdout + res.stderr
    # Simple check for common secret patterns
    assert "sk-" not in output
    assert "ADMIN_TOKEN" not in output
    # Check if header exists
    assert "--- Diagnóstico" in output

def test_expected_categories():
    script_content = Path("scripts/diagnose-readiness-warnings-local.sh").read_text()
    assert "probe_bug" in script_content
    assert "real_issue" in script_content
    assert "environment_state" in script_content
    assert "needs_config" in script_content
