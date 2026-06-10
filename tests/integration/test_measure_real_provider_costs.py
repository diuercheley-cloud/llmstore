import json
import subprocess


def test_measure_script_help():
    result = subprocess.run(["./scripts/dev/measure-real-provider-costs.sh", "--help"], capture_output=True, text=True)
    assert "Usage:" in result.stdout

def test_measure_script_dry_run(tmp_path):
    out_dir = tmp_path / "costs"
    result = subprocess.run([
        "./scripts/dev/measure-real-provider-costs.sh", 
        "--dry-run", 
        "--providers", "mock,openai", 
        "--output-dir", str(out_dir)
    ], capture_output=True, text=True)
    
    assert result.returncode == 0
    assert "Provider Costs Table" in result.stdout
    
    runs = [d for d in out_dir.iterdir() if d.is_dir()]
    assert len(runs) == 1
    
    json_path = runs[0] / "provider-costs.json"
    assert json_path.exists()
    
    with open(json_path) as f:
        data = json.load(f)
        assert len(data) == 2
        
def test_measure_script_validation_fail(tmp_path):
    out_dir = tmp_path / "costs"
    result = subprocess.run([
        "./scripts/dev/measure-real-provider-costs.sh", 
        "--dry-run", 
        "--real"
    ], capture_output=True, text=True)
    assert result.returncode != 0
    assert "Cannot specify both --real and --dry-run" in result.stdout
