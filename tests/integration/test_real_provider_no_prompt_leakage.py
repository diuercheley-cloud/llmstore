import json
import subprocess


def test_no_prompt_leakage(tmp_path):
    out_dir = tmp_path / "artifacts"
    out_dir.mkdir()
    file_path = out_dir / "test.json"
    with open(file_path, "w") as f:
        json.dump({"prompt": "sensitive query", "response": "sensitive answer"}, f)

    res = subprocess.run(
        ["./scripts/dev/scan-real-provider-artifacts.sh", "--path", str(out_dir), "--redact"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0

    with open(file_path) as f:
        data = json.load(f)
        assert "__redacted_sha256" in data["prompt"]
        assert "sensitive query" not in data["prompt"]
        assert "__redacted_sha256" in data["response"]
        assert "sensitive answer" not in data["response"]
