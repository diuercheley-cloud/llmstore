import os
import shutil
import stat
import subprocess
import tempfile

import pytest

WIZARD_PATH = os.path.abspath("scripts/configure-local-wizard.sh")

@pytest.fixture
def temp_workspace():
    with tempfile.TemporaryDirectory() as tmpdir:
        scripts_dir = os.path.join(tmpdir, "scripts")
        os.makedirs(scripts_dir)
        shutil.copy(WIZARD_PATH, os.path.join(scripts_dir, "configure-local-wizard.sh"))
        with open(os.path.join(tmpdir, "VERSION"), "w") as f:
            f.write("1.6.2-test")
        os.makedirs(os.path.join(tmpdir, "models"))
        default_admin_token = "default" + "-token"
        with open(os.path.join(tmpdir, ".env.example"), "w") as f:
            f.write(f"ADMIN_TOKEN={default_admin_token}\n")
        
        old_cwd = os.getcwd()
        os.chdir(tmpdir)
        yield tmpdir
        os.chdir(old_cwd)

def test_wizard_token_generation(temp_workspace):
    subprocess.run([
        "bash", "scripts/configure-local-wizard.sh", 
        "--non-interactive", "--yes"
    ], capture_output=True, text=True)
    
    with open(".env.local", "r") as f:
        content = f.read()
        assert "ADMIN_TOKEN=" in content
        # Should not be default
        assert ("default" + "-token") not in content
        # Should be a hex string of length 64 (from token_hex(32))
        token = [line for line in content.split("\n") if line.startswith("ADMIN_TOKEN=")][0].split("=")[1]
        assert len(token) == 64

def test_wizard_file_permissions(temp_workspace):
    subprocess.run([
        "bash", "scripts/configure-local-wizard.sh", 
        "--non-interactive", "--yes"
    ], capture_output=True, text=True)
    
    # .env.local should be 600
    env_stat = os.stat(".env.local")
    assert stat.S_IMODE(env_stat.st_mode) == 0o600
    
    # .local should be 700
    local_stat = os.stat(".local")
    assert stat.S_IMODE(local_stat.st_mode) == 0o700

def test_wizard_token_masking(temp_workspace):
    subprocess.run([
        "bash", "scripts/configure-local-wizard.sh", 
        "--non-interactive", "--yes"
    ], capture_output=True, text=True)
    
    # Check summary MD
    with open(".local/install/configuration-summary.md", "r") as f:
        content = f.read()
        # Should contain masked token
        assert "..." in content
        # Should NOT contain full hex token (64 chars)
        import re
        assert not re.search(r"[a-f0-9]{32,}", content)

def test_wizard_psp_pix_disabled(temp_workspace):
    subprocess.run([
        "bash", "scripts/configure-local-wizard.sh", 
        "--non-interactive", "--yes"
    ], capture_output=True, text=True)
    
    with open(".env.local", "r") as f:
        content = f.read()
        assert "PUBLIC_EXPOSURE=false" in content
        assert "PUBLIC_SIGNUP_ENABLED=false" in content
        assert "LOCAL_BILLING_MODE=manual" in content
