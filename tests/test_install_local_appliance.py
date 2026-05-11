import subprocess
import os
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
INSTALLER = ROOT_DIR / "scripts" / "install-local-appliance.sh"

def test_installer_exists():
    assert INSTALLER.exists()
    assert os.access(INSTALLER, os.X_OK)

def test_installer_help():
    result = subprocess.run([str(INSTALLER), "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "Usage:" in result.stdout
    assert "--dry-run" in result.stdout

def test_installer_dry_run():
    result = subprocess.run([str(INSTALLER), "--dry-run"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "[DRY-RUN]" in result.stdout
    assert "Dry-run report generated at:" in result.stdout
