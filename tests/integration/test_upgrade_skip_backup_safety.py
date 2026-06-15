import subprocess


def test_upgrade_skip_backup_fails_without_yes():
    result = subprocess.run(
        ["./scripts/deploy/upgrade-local.sh", "--to-version", "HEAD", "--skip-backup", "--dry-run"],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert (
        "exige a confirmação com --yes" in result.stdout
        or "exige a confirmação com --yes" in result.stderr
    )


def test_upgrade_skip_backup_with_yes_logs_risk():
    result = subprocess.run(
        [
            "./scripts/deploy/upgrade-local.sh",
            "--to-version",
            "HEAD",
            "--skip-backup",
            "--yes",
            "--dry-run",
        ],
        capture_output=True,
        text=True,
    )
    assert "Pular backup foi solicitado e confirmado" in result.stdout
