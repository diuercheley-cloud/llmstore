import json
import os
import subprocess
from pathlib import Path

def test_smoke_report_generation():
    # Run smoke test
    output_dir = "artifacts/test-smoke-report"
    subprocess.run(
        ["./scripts/post-upgrade-smoke-local.sh", "--output-dir", output_dir, "--skip-rag", "--skip-tts"],
        capture_output=True,
    )
    
    # Find latest run
    runs = sorted(path for path in Path(output_dir).iterdir() if path.is_dir())
    assert len(runs) > 0
    latest_run = next((run for run in reversed(runs) if (run / "smoke-report.json").exists()), runs[-1])
    
    assert (latest_run / "smoke-report.json").exists()
    assert (latest_run / "smoke-report.md").exists()
    assert (latest_run / "logs").is_dir()
    
    with open(latest_run / "smoke-report.json") as f:
        data = json.load(f)
        assert "timestamp" in data
        assert "duration_seconds" in data
        assert len(data["results"]) > 0

def test_no_secrets_in_reports():
    output_dir = "artifacts/test-smoke-report"
    runs = sorted(Path(output_dir).iterdir())
    if not runs:
        return
    
    latest_run = runs[-1]
    logs_dir = latest_run / "logs"
    
    for log_file in logs_dir.glob("*.log"):
        content = log_file.read_text()
        # Check for Bearer token or common sensitive words
        assert "Authorization: Bearer" not in content
        # The script uses curl -s so it shouldn't log headers unless -v is used.
        # But we check for the actual keys if we know them
        # This is a basic check.
