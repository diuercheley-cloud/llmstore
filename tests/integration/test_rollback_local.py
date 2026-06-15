import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]


def test_rollback_help():
    cmd = [str(ROOT_DIR / "scripts" / "rollback-local.sh"), "--help"]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT_DIR))
    assert result.returncode == 0
    assert "Uso:" in result.stdout


def test_rollback_invalid_backup():
    cmd = [
        str(ROOT_DIR / "scripts" / "rollback-local.sh"),
        "--to-version",
        "v1.0.0",
        "--backup-id",
        "/tmp/non-existent-backup-12345",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT_DIR))
    assert result.returncode != 0
    assert "O diretório de backup não foi encontrado" in result.stdout
