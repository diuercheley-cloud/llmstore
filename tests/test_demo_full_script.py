import os
import subprocess

def test_demo_full_script_exists():
    assert os.path.exists("scripts/demo-full-local.sh")

def test_demo_full_script_is_executable():
    assert os.access("scripts/demo-full-local.sh", os.X_OK)

def test_demo_full_script_help():
    result = subprocess.run(["./scripts/demo-full-local.sh", "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "Usage:" in result.stdout
    assert "--no-build" in result.stdout

def test_demo_full_script_no_secrets():
    with open("scripts/demo-full-local.sh", "r") as f:
        content = f.read()
    
    # Check for potential hardcoded secrets
    assert "sk-" not in content
    assert "ADMIN_TOKEN=" not in content # Should be picked from env or common.sh

def test_demo_full_script_safe_paths():
    with open("scripts/demo-full-local.sh", "r") as f:
        content = f.read()
    
    # Ensure it uses ARTIFACT_DIR or relative paths, not hardcoded absolute paths outside project
    assert "/home/" not in content or "$ROOT_DIR" in content
    assert "artifacts/local-demo" in content

def test_validate_demo_client_portal_does_not_reactivate_stack():
    with open("scripts/validate-demo-client-portal.sh", "r") as f:
        content = f.read()

    assert "activate.sh" not in content
    assert "init_stack_env" in content
