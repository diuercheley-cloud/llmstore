import glob
import json
import os
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
INSTALLER = ROOT_DIR / "scripts" / "install-local-appliance.sh"


def test_dry_run_report_generation():
    # Run dry-run
    result = subprocess.run([str(INSTALLER), "--dry-run"], capture_output=True, text=True)
    assert result.returncode == 0

    # Find generated dry-run report
    report_dirs = glob.glob(str(ROOT_DIR / "artifacts/install-local-appliance/*-dryrun"))
    assert len(report_dirs) > 0

    latest_report_dir = max(report_dirs, key=os.path.getmtime)
    report_json_path = Path(latest_report_dir) / "install-report.json"
    report_md_path = Path(latest_report_dir) / "install-report.md"

    assert report_json_path.exists()
    assert report_md_path.exists()

    with open(report_json_path) as f:
        data = json.load(f)
        assert data["dry_run"] is True
        assert "version" in data
