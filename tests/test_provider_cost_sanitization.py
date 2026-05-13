import pytest
import subprocess
import json
from pathlib import Path

def test_sanitization_no_secrets(tmp_path):
    out_dir = tmp_path / "costs"
    result = subprocess.run([
        "./scripts/measure-real-provider-costs.sh", 
        "--dry-run", 
        "--providers", "openai", 
        "--output-dir", str(out_dir)
    ], capture_output=True, text=True)
    
    assert result.returncode == 0
    runs = [d for d in out_dir.iterdir() if d.is_dir()]
    json_path = runs[0] / "provider-costs.json"
    
    with open(json_path) as f:
        data = json.load(f)
        for entry in data:
            # Check there are no sensitive keys
            keys = str(entry.keys()).lower()
            assert "api_key" not in keys
            assert "secret" not in keys
            assert "prompt_text" not in keys
            assert "response_text" not in keys
            
            # Values should not contain obvious mock secrets
            values = str(entry.values()).lower()
            assert "sk-" not in values
