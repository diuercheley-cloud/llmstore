import subprocess
import pytest

def test_upgrade_dry_run_creates_backup():
    result = subprocess.run(
        ["./scripts/upgrade-local.sh", "--to-version", "HEAD", "--dry-run"],
        capture_output=True,
        text=True
    )
    assert "Criando backup de segurança" in result.stdout

def test_upgrade_references_backup_script():
    result = subprocess.run(
        ["./scripts/upgrade-local.sh", "--to-version", "HEAD", "--dry-run"],
        capture_output=True,
        text=True
    )
    assert "scripts/backup-local.sh" in result.stdout
