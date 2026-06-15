import json
import subprocess


def test_margin_visibility(tmp_path):
    out_dir = tmp_path / "billing"
    res = subprocess.run(
        [
            "./scripts/validators/validate-real-billing-margin.sh",
            "--dry-run",
            "--output-dir",
            str(out_dir),
        ],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0

    runs = [d for d in out_dir.iterdir() if d.is_dir()]
    json_path = runs[0] / "billing-margin-report.json"

    with open(json_path) as f:
        data = json.load(f)
        assert data["visibility"]["admin_can_see_margin"] is True
        assert data["visibility"]["client_can_see_margin"] is False
