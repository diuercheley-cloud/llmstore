import json
import os
import subprocess


def test_skip_policy(tmp_path):
    out_dir = tmp_path / "e2e"
    env = os.environ.copy()
    
    # Remove keys to force skip
    for p in ["OPENAI_API_KEY", "DEEPSEEK_API_KEY", "ANTHROPIC_API_KEY"]:
        env.pop(p, None)
        
    res = subprocess.run([
        "./scripts/validate-real-providers-e2e.sh",
        "--real",
        "--output-dir", str(out_dir)
    ], capture_output=True, text=True, env=env)
    
    assert res.returncode == 0
    runs = [d for d in out_dir.iterdir() if d.is_dir()]
    json_path = runs[0] / "real-provider-e2e.json"
    
    with open(json_path) as f:
        data = json.load(f)
        assert data["status"] == "REAL_PROVIDER_E2E_SKIPPED"
        assert len(data["providers_skipped"]) == 3
        assert len(data["providers_configured"]) == 0
