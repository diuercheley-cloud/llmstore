import subprocess
import json
import pytest
import os
import sys

# Ensure project root is in path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def run_agentctl(*args):
    cmd = ["uv", "run", "python3", "scripts/agentctl.py"] + list(args)
    return subprocess.run(cmd, capture_output=True, text=True)

def test_agentctl_validate():
    # Valid workflow
    res = run_agentctl("validate", "tests/data/test_workflow.yaml")
    assert res.returncode == 0
    assert "is valid" in res.stdout

    # Invalid workflow
    with open("tests/data/invalid_workflow.yaml", "w") as f:
        f.write("description: incomplete")
    
    res = run_agentctl("validate", "tests/data/invalid_workflow.yaml")
    assert res.returncode != 0
    assert "Validation failed" in res.stdout
    os.remove("tests/data/invalid_workflow.yaml")

def test_agentctl_explain():
    res = run_agentctl("explain", "tests/data/test_workflow.yaml")
    assert res.returncode == 0
    assert "Workflow: Test Workflow" in res.stdout
    assert "Step 1 (llm)" in res.stdout

def test_agentctl_redaction():
    # We will fix the import in a separate turn to avoid too many changes in one go
    from scripts.agentctl_pkg.utils import redact_sensitive_data
    
    data = {
        "api_key": "sk-example1234567890abcdef1234567890",
        "nested": {"secret_token": "test-admin-token-mock-value"},
        "normal": "value"
    }
    redacted = redact_sensitive_data(data)
    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["nested"]["secret_token"] == "[REDACTED]"
    assert redacted["normal"] == "value"

def test_agentctl_api_unavailable():
    # Set a wrong API URL to force connection error
    env = os.environ.copy()
    env["CONTROL_PLANE_URL"] = "http://localhost:1" 
    
    # We need to run subprocess with this env
    cmd = ["uv", "run", "python3", "scripts/agentctl.py", "costs"]
    res = subprocess.run(cmd, capture_output=True, text=True, env=env)
    
    assert res.returncode != 0
    assert "is unavailable" in res.stderr or "Failed to fetch costs" in res.stderr
