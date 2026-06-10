# tests/test_release_summaries_no_tokens.py
# FAKE SECRET FOR TESTS ONLY
import subprocess
from pathlib import Path

import pytest

# Path to the script to test
ROOT_DIR = Path(__file__).resolve().parents[2]
VALIDATE_SCRIPT = ROOT_DIR / "scripts" / "validate-release-artifacts-security.sh"

@pytest.fixture
def temp_release_dir(tmp_path):
    """Creates a temporary release directory for testing."""
    release_dir = tmp_path / "releases" / "v-test-safe"
    release_dir.mkdir(parents=True)
    return release_dir

def run_validation(release_dir):
    """Runs the validation script on the given directory."""
    result = subprocess.run(
        [str(VALIDATE_SCRIPT), "--release-dir", str(release_dir)],
        capture_output=True,
        text=True,
        cwd=str(ROOT_DIR)
    )
    return result

def test_safe_release_passes(temp_release_dir):
    """Validates that a safe release passes."""
    (temp_release_dir / "summary.json").write_text('{"status": "success", "token": "__redacted__"}')
    (temp_release_dir / "summary.md").write_text("# Release Summary\nAll tests passed. Token is redacted.")
    (temp_release_dir / "bundle-checksums.sha256").write_text(
        "a" * 64 + "  llm-inference-stack-v1.0.0.tar.gz"
    )
    
    result = run_validation(temp_release_dir)
    assert result.returncode == 0
    assert "SUCCESS" in result.stdout

def test_detects_sk_token(temp_release_dir):
    """Validates that sk- tokens are detected."""
    (temp_release_dir / "summary.json").write_text('{"api_key": "sk-abc123abc123abc123abc123abc123"}')
    
    result = run_validation(temp_release_dir)
    assert result.returncode != 0
    assert "FAIL: Found potential secrets" in result.stdout
    assert "sk-abc123abc123abc123abc123abc123" in result.stdout

def test_detects_admin_token(temp_release_dir):
    """Validates that ADMIN_TOKEN is detected."""
    (temp_release_dir / "summary.md").write_text("The token was ADMIN_TOKEN=mysecrettoken123")
    
    result = run_validation(temp_release_dir)
    assert result.returncode != 0
    assert "FAIL: Found potential secrets" in result.stdout
    assert "ADMIN_TOKEN=mysecrettoken123" in result.stdout

def test_detects_bearer_token(temp_release_dir):
    """Validates that Bearer tokens are detected."""
    (temp_release_dir / "manifest.json").write_text('{"auth": "Bearer abcdef1234567890abcdef1234567890"}')
    
    result = run_validation(temp_release_dir)
    assert result.returncode != 0
    assert "FAIL: Found potential secrets" in result.stdout
    assert "Bearer abcdef1234567890abcdef1234567890" in result.stdout

def test_detects_logs_directory(temp_release_dir):
    """Validates that logs/ directory is detected."""
    logs_dir = temp_release_dir / "logs"
    logs_dir.mkdir()
    (logs_dir / "test.log").write_text("some log")
    
    result = run_validation(temp_release_dir)
    assert result.returncode != 0
    assert "FAIL: Found logs/ directories" in result.stdout

def test_detects_sensitive_files(temp_release_dir):
    """Validates that sensitive files like .env are detected."""
    (temp_release_dir / ".env").write_text("SECRET=123")
    
    result = run_validation(temp_release_dir)
    assert result.returncode != 0
    assert "FAIL: Found sensitive files" in result.stdout

def test_invalid_checksum_format(temp_release_dir):
    """Validates that invalid checksum format is detected."""
    (temp_release_dir / "bundle-checksums.sha256").write_text("invalid format")
    
    result = run_validation(temp_release_dir)
    assert result.returncode != 0
    assert "FAIL: Invalid lines or unallowed filenames" in result.stdout

def test_unallowed_filename_in_checksum(temp_release_dir):
    """Validates that unallowed filenames in checksum are detected."""
    (temp_release_dir / "bundle-checksums.sha256").write_text(
        "a" * 64 + "  some-other-file.txt"
    )
    
    result = run_validation(temp_release_dir)
    assert result.returncode != 0
    assert "FAIL: Invalid lines or unallowed filenames" in result.stdout

if __name__ == "__main__":
    # Allow running this script directly
    pytest.main([__file__])
