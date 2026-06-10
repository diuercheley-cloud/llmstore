import subprocess


def test_first_run_no_secrets_in_script():
    with open("scripts/deploy/first-run-local.sh", "r") as f:
        content = f.read()
    # Basic check to ensure no hardcoded secrets or echo of variables that could be secrets
    assert 'echo "$ADMIN_TOKEN"' not in content
    assert 'echo $ADMIN_TOKEN' not in content
    assert 'echo "$NEW_TOKEN"' not in content

def test_validate_first_run_local_script_dry_run():
    result = subprocess.run(["./scripts/legacy/validate-first-run-local.sh", "--dry-run"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "Validating help output" in result.stdout

def test_validate_first_run_local_script_execution():
    result = subprocess.run(["./scripts/legacy/validate-first-run-local.sh"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "[TEST] All validation passed." in result.stdout
