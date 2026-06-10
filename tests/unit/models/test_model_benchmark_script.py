import json
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def temp_output_dir(tmp_path):
    return tmp_path / "benchmarks"

def test_benchmark_script_quick_run(temp_output_dir):
    script_path = Path(__file__).resolve().parents[3] / "scripts" / "benchmark-model-local.sh"
    
    result = subprocess.run([
        str(script_path),
        "--model", "test-model-mock",
        "--quick",
        "--output-dir", str(temp_output_dir)
    ], capture_output=True, text=True)
    
    assert result.returncode == 0, f"Script failed with output: {result.stderr}"
    
    # Verify folder structure
    model_dir = temp_output_dir / "test-model-mock"
    assert model_dir.exists(), "Model directory was not created"
    
    # Get latest timestamp dir
    timestamp_dirs = sorted(model_dir.iterdir())
    assert len(timestamp_dirs) > 0, "No timestamp directory created"
    
    latest_dir = timestamp_dirs[-1]
    assert (latest_dir / "benchmark.json").exists()
    assert (latest_dir / "benchmark.md").exists()
    assert (latest_dir / "raw-results.jsonl").exists()

def test_benchmark_script_error_handling(temp_output_dir):
    script_path = Path(__file__).resolve().parents[3] / "scripts" / "benchmark-model-local.sh"
    
    # Running with a model that doesn't exist should still produce a report but with 100% error rate
    result = subprocess.run([
        str(script_path),
        "--model", "missing-model-123",
        "--quick",
        "--output-dir", str(temp_output_dir)
    ], capture_output=True, text=True)
    
    model_dir = temp_output_dir / "missing-model-123"
    assert model_dir.exists()
    
    latest_dir = sorted(model_dir.iterdir())[-1]
    
    with open(latest_dir / "benchmark.json", "r") as f:
        data = json.load(f)
        
    assert data["error_rate"] == 1.0, "Expected 100% error rate for missing model"
