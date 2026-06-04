import subprocess


def test_first_run_help():
    result = subprocess.run(["./scripts/first-run-local.sh", "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "Usage:" in result.stdout
    assert "--with-demo" in result.stdout

def test_first_run_dry_run():
    result = subprocess.run(["./scripts/first-run-local.sh", "--dry-run"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "[DRY-RUN] Would execute first-run setup" in result.stdout
