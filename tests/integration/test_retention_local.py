import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def test_env(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    
    # Create structure
    (project_root / "config").mkdir()
    (project_root / "scripts").mkdir()
    (project_root / "artifacts").mkdir()
    (project_root / "data").mkdir()
    (project_root / "logs").mkdir()
    (project_root / "models").mkdir()
    (project_root / "releases").mkdir()
    
    # Copy script and common.sh (or mock them)
    # Actually, we can point PROJECT_ROOT to this tmp project.
    # We need common.sh if the script sources it.
    # Let's create a minimal common.sh
    common_sh = project_root / "scripts" / "common.sh"
    common_sh.write_text("#!/usr/bin/env bash\ninit_stack_env() { :; }\n")
    
    retention_script = project_root / "scripts" / "retention-local.sh"
    # Copy real script to tmp project
    real_script_path = Path(__file__).resolve().parents[2] / "scripts" / "retention-local.sh"
    shutil.copy(real_script_path, retention_script)
    retention_script.chmod(0o755)
    
    # Default config
    config_path = project_root / "config" / "retention-example.json"
    config_data = {
        "rag_uploads_retention_days": None,
        "tts_audio_retention_days": 7,
        "validation_artifacts_keep_last": 10,
        "demo_artifacts_keep_last": 5,
        "security_reports_keep_last": 10,
        "production_readiness_keep_last": 10,
        "dr_artifacts_keep_last": 5,
        "model_benchmarks_keep_last": 10,
        "backups_keep_last": 5,
        "logs_retention_days": 14,
        "releases_keep_all": True
    }
    config_path.write_text(json.dumps(config_data))
    
    return project_root

def run_retention(project_root, args):
    env = os.environ.copy()
    env["PROJECT_ROOT"] = str(project_root)
    script_path = project_root / "scripts" / "retention-local.sh"
    result = subprocess.run([str(script_path)] + args, env=env, capture_output=True, text=True)
    return result

def test_help(test_env):
    result = run_retention(test_env, ["--help"])
    assert result.returncode == 0
    assert "Usage:" in result.stdout

def test_dry_run_no_deletion(test_env):
    # Create some artifacts
    artifacts_dir = test_env / "artifacts" / "validation"
    artifacts_dir.mkdir(parents=True)
    for i in range(15):
        (artifacts_dir / f"test-{i}").touch()
    
    result = run_retention(test_env, ["--dry-run", "--section", "artifacts"])
    assert result.returncode == 0
    assert "DRY RUN: No files were deleted." in result.stdout
    assert len(list(artifacts_dir.glob("*"))) == 15

def test_artifact_retention(test_env):
    artifacts_dir = test_env / "artifacts" / "validation"
    artifacts_dir.mkdir(parents=True)
    # Create 15 files with different timestamps
    for i in range(15):
        f = artifacts_dir / f"test-{i}"
        f.touch()
        # Set mtime to ensure sorting (oldest first)
        os.utime(f, (1000, 1000 + i))
    
    # We keep 10, so 5 should be deleted.
    # The script uses ls -dt, which is newest first.
    # It keeps newest 10, deletes oldest 5.
    
    result = run_retention(test_env, ["--yes", "--section", "artifacts"])
    assert result.returncode == 0
    remaining = list(artifacts_dir.glob("*"))
    assert len(remaining) == 10

def test_log_retention(test_env):
    import time
    logs_dir = test_env / "logs"
    old_log = logs_dir / "old.log"
    new_log = logs_dir / "new.log"
    old_log.touch()
    new_log.touch()
    
    # Set old_log to 20 days ago
    twenty_days_ago = time.time() - (20 * 24 * 3600)
    os.utime(old_log, (twenty_days_ago, twenty_days_ago))
    
    result = run_retention(test_env, ["--yes", "--section", "logs"])
    assert result.returncode == 0
    assert not old_log.exists()
    assert new_log.exists()
