import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]


def test_upgrade_help():
    cmd = [str(ROOT_DIR / "scripts" / "upgrade-local.sh"), "--help"]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT_DIR))
    assert result.returncode == 0
    assert "Uso:" in result.stdout


def test_upgrade_dry_run_complex():
    with open(ROOT_DIR / "VERSION") as f:
        version = f.read().strip()

    cmd = [
        str(ROOT_DIR / "scripts" / "upgrade-local.sh"),
        "--to-version",
        version,
        "--dry-run",
        "--skip-backup",
        "--no-build",
        "--yes",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT_DIR))
    assert result.returncode == 0
    assert "Pular backup foi solicitado e confirmado" in result.stdout
    assert "Simulação de upgrade (dry-run) concluída com sucesso" in result.stdout
