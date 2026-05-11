import subprocess
import os
import shutil
import tempfile
import pytest

WIZARD_PATH = os.path.abspath("scripts/configure-local-wizard.sh")

@pytest.fixture
def temp_workspace():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Setup mock workspace
        scripts_dir = os.path.join(tmpdir, "scripts")
        os.makedirs(scripts_dir)
        shutil.copy(WIZARD_PATH, os.path.join(scripts_dir, "configure-local-wizard.sh"))
        
        with open(os.path.join(tmpdir, "VERSION"), "w") as f:
            f.write("1.6.2-test")
            
        os.makedirs(os.path.join(tmpdir, "models"))
        
        # Create .env.example
        default_admin_token = "default" + "-token"
        with open(os.path.join(tmpdir, ".env.example"), "w") as f:
            f.write(f"ADMIN_TOKEN={default_admin_token}\nBASE_URL=http://localhost\n")
            
        old_cwd = os.getcwd()
        os.chdir(tmpdir)
        yield tmpdir
        os.chdir(old_cwd)

def test_wizard_help(temp_workspace):
    result = subprocess.run(["bash", "scripts/configure-local-wizard.sh", "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "Usage:" in result.stdout

def test_wizard_non_interactive_defaults(temp_workspace):
    result = subprocess.run([
        "bash", "scripts/configure-local-wizard.sh", 
        "--non-interactive", "--yes"
    ], capture_output=True, text=True)
    assert result.returncode == 0
    
    assert os.path.exists(".env.local")
    with open(".env.local", "r") as f:
        content = f.read()
        assert "LOCAL_APPLIANCE_MODE=true" in content
        assert "BASE_URL=http://localhost:18080" in content

def test_wizard_custom_values(temp_workspace):
    result = subprocess.run([
        "bash", "scripts/configure-local-wizard.sh", 
        "--non-interactive", "--yes",
        "--base-url", "http://my-appliance.local",
        "--host-port", "9090",
        "--gpu",
        "--enable-demo"
    ], capture_output=True, text=True)
    assert result.returncode == 0
    
    with open(".env.local", "r") as f:
        content = f.read()
        assert "BASE_URL=http://my-appliance.local" in content
        assert "HOST_PORT=9090" in content
        assert "LLAMA_N_GPU_LAYERS=20" in content
        assert "DEMO_MODE=true" in content

def test_wizard_backup(temp_workspace):
    # Create initial .env.local
    with open(".env.local", "w") as f:
        f.write("INITIAL=TRUE\n")
        
    subprocess.run([
        "bash", "scripts/configure-local-wizard.sh", 
        "--non-interactive", "--yes"
    ], capture_output=True, text=True)
    
    backup_dir = ".local/backups/env"
    assert os.path.exists(backup_dir)
    backups = os.listdir(backup_dir)
    assert len(backups) == 1
    assert backups[0].endswith(".bak")

def test_wizard_dry_run(temp_workspace):
    result = subprocess.run([
        "bash", "scripts/configure-local-wizard.sh", 
        "--non-interactive", "--dry-run",
        "--base-url", "http://dry-run.local"
    ], capture_output=True, text=True)
    assert result.returncode == 0
    assert "No changes were made." in result.stdout
    assert not os.path.exists(".env.local")
