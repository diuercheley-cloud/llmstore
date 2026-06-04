import shutil
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent

def run_script(script_name, args=None, input_text=None):
    cmd = [str(ROOT_DIR / "scripts" / script_name)]
    if args:
        cmd.extend(args)
    
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        input=input_text,
        cwd=str(ROOT_DIR)
    )

def test_upgrade_requires_to_version():
    result = run_script("upgrade-local.sh", [])
    assert result.returncode != 0
    assert "Erro: --to-version é obrigatório" in result.stdout

def test_rollback_requires_to_version_and_backup():
    result = run_script("rollback-local.sh", [])
    assert result.returncode != 0
    assert "Erro: --to-version e --backup-id são obrigatórios" in result.stdout

def test_upgrade_dry_run():
    # Detect current version from file
    with open(ROOT_DIR / "VERSION", "r") as f:
        version = f.read().strip()
    
    result = run_script("upgrade-local.sh", ["--to-version", version, "--dry-run"])
    assert result.returncode == 0
    assert "[upgrade] Dry-run concluído com sucesso" in result.stdout
    assert "Upgrade Workflow" in result.stdout

def test_rollback_dry_run():
    mock_backup = ROOT_DIR / "artifacts" / "backups-local" / "mock-test"
    mock_backup.mkdir(parents=True, exist_ok=True)
    
    result = run_script("rollback-local.sh", [
        "--to-version", "v1.0.0", 
        "--backup-id", str(mock_backup), 
        "--dry-run", 
        "--yes"
    ])
    
    assert result.returncode == 0
    assert "[rollback] Dry-run concluído com sucesso" in result.stdout
    
    shutil.rmtree(mock_backup)

def test_rollback_strong_confirmation():
    mock_backup = ROOT_DIR / "artifacts" / "backups-local" / "mock-test-confirm"
    mock_backup.mkdir(parents=True, exist_ok=True)
    
    # Try with wrong confirmation
    result = run_script("rollback-local.sh", [
        "--to-version", "v1.0.0", 
        "--backup-id", str(mock_backup),
        "--skip-git-check"
    ], input_text="WRONG CONFIRM\n")
    
    assert "Abortado pelo usuário" in result.stdout
    
    shutil.rmtree(mock_backup)
