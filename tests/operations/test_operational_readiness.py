import json
import os
import subprocess
from pathlib import Path


def test_operational_readiness_script():
    # Run scripts/operational-readiness-pack.sh using bash
    project_dir = Path(__file__).resolve().parents[2]
    script_path = project_dir / "scripts" / "operational-readiness-pack.sh"
    
    # We can pass an env override or set variables
    env = os.environ.copy()
    env["READINESS_TIMEOUT"] = "5"
    
    res = subprocess.run(["bash", str(script_path)], capture_output=True, text=True, cwd=str(project_dir), env=env)
    
    assert res.returncode == 0
    assert "Readiness check complete" in res.stdout
    
    # Check that output files were generated
    checks_file = project_dir / "artifacts" / "operational-readiness" / "latest" / "checks.json"
    summary_file = project_dir / "artifacts" / "operational-readiness" / "latest" / "summary.md"
    recs_file = project_dir / "artifacts" / "operational-readiness" / "latest" / "recommendations.md"
    
    assert checks_file.exists()
    assert summary_file.exists()
    assert recs_file.exists()
    
    # Validate checks.json is valid JSON
    with open(checks_file, "r") as f:
        data = json.load(f)
        
    assert "docker_compose" in data
    assert "postgres" in data
    assert "redis" in data
    assert "health_api" in data
    assert "ready_api" in data
    assert "metrics_api" in data
    assert "timestamp" in data
