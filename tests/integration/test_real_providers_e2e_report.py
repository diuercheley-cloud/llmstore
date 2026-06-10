import json
import subprocess


def test_e2e_report_generation(tmp_path):
    out_dir = tmp_path / "e2e"
    res = subprocess.run([
        "./scripts/validators/validate-real-providers-e2e.sh",
        "--dry-run",
        "--output-dir", str(out_dir)
    ], capture_output=True, text=True)
    assert res.returncode == 0
    
    runs = [d for d in out_dir.iterdir() if d.is_dir()]
    assert len(runs) == 1
    
    json_path = runs[0] / "real-provider-e2e.json"
    with open(json_path) as f:
        data = json.load(f)
        assert "status" in data
        assert "financials" in data
        assert "providers_configured" in data
        assert "fallback_status" in data
        assert "sanitization_status" in data
