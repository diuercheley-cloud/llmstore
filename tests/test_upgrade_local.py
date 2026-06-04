import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent

def test_upgrade_help():
    cmd = [str(ROOT_DIR / "scripts" / "upgrade-local.sh"), "--help"]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT_DIR))
    assert result.returncode == 0
    assert "Uso:" in result.stdout

def test_upgrade_dry_run_complex():
    with open(ROOT_DIR / "VERSION", "r") as f:
        version = f.read().strip()
    
    cmd = [
        str(ROOT_DIR / "scripts" / "upgrade-local.sh"),
        "--to-version", version,
        "--dry-run",
        "--skip-backup",
        "--no-build"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT_DIR))
    assert result.returncode == 0
    assert "[upgrade][warn] Backup ignorado" in result.stdout
    assert "Dry-run concluído com sucesso" in result.stdout
