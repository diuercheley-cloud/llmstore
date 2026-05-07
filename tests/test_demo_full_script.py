import os
import subprocess
import pytest

SCRIPT_PATH = "scripts/demo-full-local.sh"

def test_script_exists():
    assert os.path.exists(SCRIPT_PATH)

def test_script_is_executable():
    assert os.access(SCRIPT_PATH, os.X_OK)

def test_script_help():
    result = subprocess.run([SCRIPT_PATH, "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "Uso:" in result.stdout
    assert "--no-build" in result.stdout

def test_no_secrets_in_script():
    with open(SCRIPT_PATH, "r") as f:
        content = f.read()
        # Basic check for common secret patterns (hardcoded keys)
        assert "sk-" not in content
        assert "ADMIN_TOKEN=" not in content or "ADMIN_TOKEN=\"\"" in content or "ADMIN_TOKEN=\"${" in content

def test_safe_paths():
    with open(SCRIPT_PATH, "r") as f:
        content = f.read()
        # Ensure it uses artifacts directory
        assert "artifacts/local-demo" in content
        # Ensure it doesn't use /tmp directly in a dangerous way
        assert "rm -rf /tmp" not in content
