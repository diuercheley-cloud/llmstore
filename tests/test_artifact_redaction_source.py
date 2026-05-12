# tests/test_artifact_redaction_source.py
# FAKE SECRET FOR TESTS ONLY
import os
import json
import subprocess
import pytest
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
REDACTION_SH = ROOT_DIR / "lib" / "redaction.sh"
REDACT_JSON_PY = ROOT_DIR / "redact_json.py"

def test_redaction_sh_exists():
    assert REDACTION_SH.exists()

def test_redact_json_py_exists():
    assert REDACT_JSON_PY.exists()

def test_redact_stream_bash():
    token = "sk-1234567890123456789012345"
    cmd = f'source {REDACTION_SH} && echo "my key is {token}" | redact_stream'
    result = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, check=True)
    assert token not in result.stdout
    assert "[REDACTED]" in result.stdout

def test_redact_stream_bash_safe_pattern():
    token = "sk-local-example"
    cmd = f'source {REDACTION_SH} && echo "my key is {token}" | redact_stream'
    result = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, check=True)
    assert token in result.stdout
    assert "[REDACTED]" not in result.stdout

def test_redact_json_py():
    data = {
        "key": "sk-1234567890123456789012345",
        "nested": {
            "token": "Bearer 1234567890123456789012345",
            "safe": "sk-local-example"
        },
        "list": ["ghp_123456789012345678901234567890123456"]
    }
    
    input_json = json.dumps(data)
    result = subprocess.run([str(REDACT_JSON_PY)], input=input_json, capture_output=True, text=True, check=True)
    redacted_data = json.loads(result.stdout)
    
    assert redacted_data["key"] == "[REDACTED]"
    assert redacted_data["nested"]["token"] == "Bearer [REDACTED]"
    assert redacted_data["nested"]["safe"] == "sk-local-example"
    assert redacted_data["list"][0] == "[REDACTED]"

def test_redact_json_py_preserves_structure():
    data = {"a": 1, "b": [1, 2, 3], "c": {"d": True}}
    input_json = json.dumps(data)
    result = subprocess.run([str(REDACT_JSON_PY)], input=input_json, capture_output=True, text=True, check=True)
    assert json.loads(result.stdout) == data

def test_redaction_scripts_referenced():
    # Check if key scripts reference redaction
    scripts_to_check = [
        "scripts/validate-local-production-full.sh",
        "scripts/release-local-production.sh",
        "scripts/security-report-local.sh",
        "scripts/production-readiness-local.sh",
        "scripts/demo-full-local.sh",
        "lib/validation-logging.sh"
    ]
    
    for script in scripts_to_check:
        script_path = ROOT_DIR / script
        assert script_path.exists()
        content = script_path.read_text()
        assert "redact" in content.lower()
