import os
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CLEAN_SCRIPT = PROJECT_ROOT / "scripts" / "clean-rag-local-data.sh"
VALIDATE_SCRIPT = PROJECT_ROOT / "scripts" / "validate-clean-rag-local-data.sh"

def test_scripts_exist():
    """Verify that the cleanup and validation scripts exist."""
    assert CLEAN_SCRIPT.exists()
    assert VALIDATE_SCRIPT.exists()

def test_scripts_are_executable():
    """Verify that the cleanup and validation scripts are executable."""
    # We will chmod them in the execution phase, but let's check here too.
    assert os.access(CLEAN_SCRIPT, os.X_OK)
    assert os.access(VALIDATE_SCRIPT, os.X_OK)

def test_clean_script_help():
    """Verify that the cleanup script provides help output."""
    result = subprocess.run([str(CLEAN_SCRIPT), "--help"], capture_output=True, text=True)
    assert "Usage:" in result.stdout

def test_path_protection_logic():
    """Verify that the cleanup script contains path protection logic."""
    with open(CLEAN_SCRIPT, "r") as f:
        content = f.read()
    
    # Check for safety guards
    assert 'rm -rf "$t"' in content
    assert 'if [[ "$t" != "${PROJECT_ROOT}"/* ]]; then' in content
    assert 'case "$t" in' in content
    assert '*"models"*' in content
    assert '*"scripts"*' in content
    assert 'PROTECTED PATH' in content

def test_dry_run_safety():
    """Verify that --dry-run does not perform deletions (via output message)."""
    # Create a dummy file that should be caught by the script
    dummy_dir = PROJECT_ROOT / "data" / "rag_uploads-test-dry-run"
    dummy_dir.mkdir(parents=True, exist_ok=True)
    dummy_file = dummy_dir / "test.txt"
    dummy_file.write_text("test")
    
    try:
        result = subprocess.run([str(CLEAN_SCRIPT), "--dry-run"], capture_output=True, text=True)
        assert "DRY RUN: No files were deleted" in result.stdout
        assert dummy_file.exists()
    finally:
        # Cleanup
        if dummy_file.exists():
            dummy_file.unlink()
        if dummy_dir.exists():
            dummy_dir.rmdir()

@pytest.mark.slow
def test_validation_script_execution():
    """Run the full validation script to ensure behavioral correctness."""
    result = subprocess.run([str(VALIDATE_SCRIPT)], capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
    assert result.returncode == 0
    assert "Validation SUCCESSFUL" in result.stdout
