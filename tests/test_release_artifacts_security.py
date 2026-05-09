import os
import subprocess
from pathlib import Path

def test_validate_script_exists_and_executable():
    script_path = Path("scripts/validate-release-artifacts-security.sh")
    assert script_path.exists()
    assert os.access(script_path, os.X_OK)

def test_gitignore_rules():
    gitignore_content = Path(".gitignore").read_text()
    assert "releases/**/*.tar.gz" in gitignore_content
    assert "artifacts/" in gitignore_content

def test_no_tarballs_in_git():
    # Check if any .tar.gz is tracked in releases/
    result = subprocess.run(
        ["git", "ls-files", "releases/**/*.tar.gz"],
        capture_output=True,
        text=True
    )
    assert result.stdout.strip() == ""

def test_redaction_logic_mock():
    # Create a dummy release with a secret and check if validation fails
    dummy_release_dir = Path("releases/v9.9.9-test-security")
    dummy_release_dir.mkdir(parents=True, exist_ok=True)
    summary_file = dummy_release_dir / "summary.json"
    
    try:
        # Test with secret
        fake_secret = "sk-" + "123456789012345678901234567890"
        summary_file.write_text(f'{{"token": "{fake_secret}"}}')
        result = subprocess.run(
            ["./scripts/validate-release-artifacts-security.sh"],
            capture_output=True,
            text=True
        )
        assert result.returncode != 0
        assert "FAIL: Found potential secrets" in result.stdout
        
        # Test with redacted token
        summary_file.write_text('{"token": "__redacted__"}')
        result = subprocess.run(
            ["./scripts/validate-release-artifacts-security.sh"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "SUCCESS" in result.stdout

    finally:
        # Cleanup
        if summary_file.exists():
            summary_file.unlink()
        if dummy_release_dir.exists():
            dummy_release_dir.rmdir()

def test_logs_dir_in_releases_fails():
    dummy_release_dir = Path("releases/v9.9.9-test-logs")
    logs_dir = dummy_release_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        result = subprocess.run(
            ["./scripts/validate-release-artifacts-security.sh"],
            capture_output=True,
            text=True
        )
        assert result.returncode != 0
        assert "FAIL: Found logs/ directories" in result.stdout
    finally:
        if logs_dir.exists():
            logs_dir.rmdir()
        if dummy_release_dir.exists():
            dummy_release_dir.rmdir()
