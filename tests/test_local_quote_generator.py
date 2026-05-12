import subprocess
import json
import os
import pytest

def test_generate_quote_basic():
    cmd = [
        "bash", "scripts/generate-local-quote.sh",
        "--company-name", "Test Corp",
        "--plan", "Basic"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    assert "Quote generated successfully" in result.stdout
    
    # Extract JSON path
    json_path = None
    for line in result.stdout.splitlines():
        if line.startswith("JSON: "):
            json_path = line.replace("JSON: ", "").strip()
            break
    
    assert json_path is not None
    assert os.path.exists(json_path)
    
    with open(json_path, 'r') as f:
        data = json.load(f)
        assert data["company_name"] == "Test Corp"
        assert data["plan"] == "Basic"
        assert data["totals"]["setup"] == 1500
        assert data["totals"]["recurring"] == 500

def test_generate_quote_with_extras():
    cmd = [
        "bash", "scripts/generate-local-quote.sh",
        "--company-name", "Extra Corp",
        "--plan", "Pro",
        "--rag",
        "--support-hours", "4",
        "--discount-percent", "10"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    
    json_path = None
    for line in result.stdout.splitlines():
        if line.startswith("JSON: "):
            json_path = line.replace("JSON: ", "").strip()
            break
            
    with open(json_path, 'r') as f:
        data = json.load(f)
        # Pro setup: 5000, RAG: 2500 -> 7500
        assert data["totals"]["setup"] == 7500
        # Pro monthly: 2000, 4h support @ 250 -> 3000
        assert data["totals"]["recurring"] == 3000
        # Total: 10500, 10% discount -> 9450
        assert data["totals"]["first_month_final"] == 9450
