import json
import subprocess


def test_redaction_json(tmp_path):
    out_dir = tmp_path / "artifacts"
    out_dir.mkdir()
    file_path = out_dir / "test.json"
    with open(file_path, "w") as f:
        json.dump({"secret": "sk-12345", "other": "value"}, f)
    
    res = subprocess.run(["./scripts/scan-real-provider-artifacts.sh", "--path", str(out_dir), "--redact"], capture_output=True, text=True)
    assert res.returncode == 0
    
    with open(file_path, "r") as f:
        data = json.load(f)
        assert data["secret"] == "__redacted_provider_secret__"
        assert data["other"] == "value"
