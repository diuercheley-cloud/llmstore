import json
import subprocess


def test_sanitization(tmp_path):
    out_dir = tmp_path / "billing"
    res = subprocess.run([
        "./scripts/validate-real-billing-margin.sh",
        "--dry-run",
        "--output-dir", str(out_dir)
    ], capture_output=True, text=True)
    assert res.returncode == 0
    
    runs = [d for d in out_dir.iterdir() if d.is_dir()]
    json_path = runs[0] / "billing-margin-report.json"
    
    with open(json_path) as f:
        data = json.load(f)
        s = json.dumps(data).lower()
        assert "api_key" not in s
        assert "secret" not in s
        assert "prompt_text" not in s
        assert "response_text" not in s
