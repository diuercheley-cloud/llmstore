import json
import subprocess


def test_sanitization_is_called(tmp_path):
    out_dir = tmp_path / "e2e"
    res = subprocess.run(
        [
            "./scripts/validators/validate-real-providers-e2e.sh",
            "--dry-run",
            "--output-dir",
            str(out_dir),
        ],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0

    runs = [d for d in out_dir.iterdir() if d.is_dir()]
    json_path = runs[0] / "real-provider-e2e.json"

    with open(json_path) as f:
        data = json.load(f)
        assert data["sanitization_status"] == "PASS"
        assert data["status"] == "REAL_PROVIDER_E2E_PASS"
