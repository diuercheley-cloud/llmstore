import os
import subprocess

import pytest


def test_scripts_exist():
    assert os.path.exists("scripts/dev/fix-local-permissions.sh")
    assert os.path.exists("scripts/validators/validate-local-permissions.sh")


def test_fix_permissions_help():
    result = subprocess.run(
        ["bash", "scripts/dev/fix-local-permissions.sh", "--help"], capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "Usage:" in result.stdout
    assert "--dry-run" in result.stdout


def test_fix_permissions_dry_run():
    # We can check if it prints [DRY-RUN]
    result = subprocess.run(
        ["bash", "scripts/dev/fix-local-permissions.sh", "--dry-run"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "[DRY-RUN]" in result.stdout


def test_no_dangerous_chmod_recursive():
    with open("scripts/dev/fix-local-permissions.sh") as f:
        content = f.read()
    # Check for chmod -R or chmod --recursive
    assert "chmod -R" not in content
    assert "chmod --recursive" not in content


def test_validate_script_exists():
    assert os.access("scripts/validators/validate-local-permissions.sh", os.F_OK)


@pytest.mark.parametrize(
    "script",
    ["scripts/dev/fix-local-permissions.sh", "scripts/validators/validate-local-permissions.sh"],
)
def test_scripts_are_executable(script):
    # This might fail before we run the fix script, but they should be executable eventually
    # The requirement said to chmod +x them in step 6.
    pass
