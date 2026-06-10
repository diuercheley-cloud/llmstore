import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CLEAN_INSTALL_SCRIPT = ROOT / "scripts" / "validate-clean-install-local.sh"


def test_env_local_not_touched_by_dry_run():
    env_local = ROOT / ".env.local"
    if not env_local.exists():
        pytest.skip("No .env.local in repo to check")

    mtime_before = os.path.getmtime(env_local)

    result = subprocess.run(
        ["bash", str(CLEAN_INSTALL_SCRIPT), "--dry-run", "--skip-build"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"--dry-run failed:\n{result.stderr}"

    mtime_after = os.path.getmtime(env_local)
    assert mtime_before == mtime_after, ".env.local was modified by dry-run"


def test_models_dir_not_touched():
    models_dir = ROOT / "models"
    if models_dir.exists():
        mtime_before = os.path.getmtime(models_dir)
        result = subprocess.run(
            ["bash", str(CLEAN_INSTALL_SCRIPT), "--dry-run", "--skip-build"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0
        mtime_after = os.path.getmtime(models_dir)
        assert mtime_before == mtime_after, "models/ directory was touched by dry-run"


def test_backups_dir_not_touched():
    backups_dir = ROOT / "backups"
    if backups_dir.exists():
        mtime_before = os.path.getmtime(backups_dir)
        result = subprocess.run(
            ["bash", str(CLEAN_INSTALL_SCRIPT), "--dry-run", "--skip-build"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0
        mtime_after = os.path.getmtime(backups_dir)
        assert mtime_before == mtime_after, "backups/ directory was touched"
    else:
        pass


def test_releases_dir_not_touched():
    releases_dir = ROOT / "releases"
    if releases_dir.exists():
        mtime_before = os.path.getmtime(releases_dir)
        result = subprocess.run(
            ["bash", str(CLEAN_INSTALL_SCRIPT), "--dry-run", "--skip-build"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0
        mtime_after = os.path.getmtime(releases_dir)
        assert mtime_before == mtime_after, "releases/ directory was touched"
    else:
        pass


def test_excludes_git_from_copy():
    result = subprocess.run(
        ["bash", str(CLEAN_INSTALL_SCRIPT), "--dry-run", "--skip-build"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout.lower()
    assert "exclude" in output or ".git" in output.lower(), "Exclusion patterns not mentioned in output"


def test_dry_run_does_not_require_docker():
    result = subprocess.run(
        ["bash", str(CLEAN_INSTALL_SCRIPT), "--dry-run", "--skip-build"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, "dry-run should not fail even without Docker"
