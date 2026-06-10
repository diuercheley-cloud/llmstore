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
    (project_root / "models").mkdir()
    (project_root / "releases").mkdir()
    (project_root / "data" / "rag_uploads").mkdir(parents=True)
    
    # Minimal common.sh
    common_sh = project_root / "scripts" / "common.sh"
    common_sh.write_text("#!/usr/bin/env bash\ninit_stack_env() { :; }\n")
    
    retention_script = project_root / "scripts" / "retention-local.sh"
    real_script_path = Path(__file__).resolve().parents[2] / "scripts" / "retention-local.sh"
    shutil.copy(real_script_path, retention_script)
    retention_script.chmod(0o755)
    
    # Config that would delete everything if not protected
    config_path = project_root / "config" / "retention-example.json"
    config_data = {
        "rag_uploads_retention_days": 0,
        "logs_retention_days": 0,
        "releases_keep_all": True
    }
    import json
    config_path.write_text(json.dumps(config_data))
    
    return project_root

def run_retention(project_root, args):
    env = os.environ.copy()
    env["PROJECT_ROOT"] = str(project_root)
    script_path = project_root / "scripts" / "retention-local.sh"
    result = subprocess.run([str(script_path)] + args, env=env, capture_output=True, text=True)
    return result

def test_models_protection(test_env):
    model_file = test_env / "models" / "test.gguf"
    model_file.touch()
    
    # Even if we try to clean "all", models shouldn't be candidates
    run_retention(test_env, ["--yes", "--section", "all"])
    assert model_file.exists()

def test_releases_protection(test_env):
    release_dir = test_env / "releases" / "v1.0.0"
    release_dir.mkdir()
    (release_dir / "manifest.json").touch()
    
    # Should not be deleted by default
    run_retention(test_env, ["--yes", "--section", "all"])
    assert release_dir.exists()

def test_dot_env_protection(test_env):
    env_file = test_env / ".env"
    env_file.touch()
    
    # Should not be deleted even if it was a candidate somehow
    # (Actually it's not a candidate in any section, but protection is good)
    run_retention(test_env, ["--yes", "--section", "all"])
    assert env_file.exists()

def test_outside_project_protection(test_env, tmp_path):
    outside_file = tmp_path / "outside.txt"
    outside_file.touch()
    
    # The script should not allow deleting things outside PROJECT_ROOT
    # This is harder to test because the script finds items *under* PROJECT_ROOT.
    # But we can test is_protected logic if we could.
    pass
