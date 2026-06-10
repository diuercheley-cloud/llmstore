import pytest
import subprocess
import json
import tempfile
from pathlib import Path

# Assuming root is two levels up from scripts/validators/
ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = ROOT / "scripts/validators/check-maintenance-budgets.py"

def run_validator(config_path: Path):
    # We need to temporarily swap the config path in the validator script or pass it as an argument.
    # Given the script currently hardcodes the path, we will create a temporary config file 
    # at the location expected by the script and run it, or modify the script to accept an argument.
    # For simplicity, we'll patch the config file in place.
    
    config_file = ROOT / "config/maintenance-budgets.json"
    backup_file = ROOT / "config/maintenance-budgets.json.bak"
    
    if config_file.exists():
        config_file.rename(backup_file)
        
    try:
        # Create dummy config
        with open(config_path, 'r') as f:
            content = f.read()
        
        with open(config_file, 'w') as f:
            f.write(content)
            
        result = subprocess.run(
            ["python3", str(VALIDATOR_PATH)],
            capture_output=True,
            text=True,
            check=False
        )
        return result
    finally:
        if backup_file.exists():
            backup_file.rename(config_file)
        else:
            config_file.unlink()

def test_budget_within_limits(tmp_path):
    config = {
        "max_api_router_files": 1000,
        "max_service_files": 1000,
        "max_feature_flags": 1000,
        "max_main_lines": 10000,
        "max_settings_lines": 10000,
        "min_collected_tests": 0
    }
    config_path = tmp_path / "budgets.json"
    with open(config_path, 'w') as f:
        json.dump(config, f)
        
    result = run_validator(config_path)
    assert result.returncode == 0
    assert "PASS" in result.stdout

def test_budget_exceeded(tmp_path):
    config = {
        "max_api_router_files": 0,
        "max_service_files": 0,
        "max_feature_flags": 0,
        "max_main_lines": 0,
        "max_settings_lines": 0,
        "min_collected_tests": 1000000
    }
    config_path = tmp_path / "budgets.json"
    with open(config_path, 'w') as f:
        json.dump(config, f)
        
    result = run_validator(config_path)
    assert result.returncode == 1
    assert "FAIL" in result.stdout

def test_missing_config():
    # Remove config entirely
    config_file = ROOT / "config/maintenance-budgets.json"
    backup_file = ROOT / "config/maintenance-budgets.json.bak"
    if config_file.exists():
        config_file.rename(backup_file)
    
    try:
        result = subprocess.run(
            ["python3", str(VALIDATOR_PATH)],
            capture_output=True,
            text=True,
            check=False
        )
        assert result.returncode == 2
        assert "ERROR" in result.stdout
    finally:
        if backup_file.exists():
            backup_file.rename(config_file)
