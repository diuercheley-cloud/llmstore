import subprocess


def test_rollback_accepts_backup_id():
    result = subprocess.run(
        ["./scripts/dev/rollback-local.sh", "--to-version", "HEAD", "--backup-id", "test_backup", "--yes", "--dry-run"],
        capture_output=True,
        text=True
    )
    assert "Restaurando backup a partir de: test_backup" in result.stdout
