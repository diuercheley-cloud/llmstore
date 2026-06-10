import json
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
SCRIPT = ROOT_DIR / "scripts" / "cleanup-local-branches.sh"
ARTIFACTS_DIR = ROOT_DIR / "artifacts" / "repo-cleanup"


def _latest_report_dir():
    if not ARTIFACTS_DIR.exists():
        return None
    dirs = sorted(ARTIFACTS_DIR.iterdir())
    return str(dirs[-1]) if dirs else None


def test_script_exists():
    assert SCRIPT.exists()
    assert SCRIPT.stat().st_mode & 0o111


def test_script_has_shebang():
    first_line = SCRIPT.read_text().splitlines()[0]
    assert first_line in ("#!/usr/bin/env bash", "#!/bin/bash")


def test_dry_run_merged_only_exit_zero():
    result = subprocess.run(
        [str(SCRIPT), "--dry-run", "--merged-only"],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "DRY" in result.stdout or "dry" in result.stdout


def test_dry_run_produces_report():
    result = subprocess.run(
        [str(SCRIPT), "--dry-run", "--merged-only"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "Report:" in result.stdout
    report_dir = _latest_report_dir()
    assert report_dir is not None


def test_report_json_valid():
    result = subprocess.run(
        [str(SCRIPT), "--dry-run", "--merged-only"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    report_dir = _latest_report_dir()
    assert report_dir is not None
    report_json = Path(report_dir) / "branches-cleanup-report.json"
    assert report_json.exists()
    data = json.loads(report_json.read_text())
    assert isinstance(data, list)
    for entry in data:
        assert "branch" in entry
        assert "merged" in entry
        assert "recommendation" in entry


def test_report_md_exists():
    result = subprocess.run(
        [str(SCRIPT), "--dry-run", "--merged-only"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    report_dir = _latest_report_dir()
    assert report_dir is not None
    report_md = Path(report_dir) / "branches-cleanup-report.md"
    assert report_md.exists()
    content = report_md.read_text()
    assert "Local Branch Cleanup Report" in content


def test_current_branch_is_protected():
    current = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True, text=True
    ).stdout.strip()
    result = subprocess.run(
        [str(SCRIPT), "--dry-run"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert current in result.stdout
    report_dir = _latest_report_dir()
    assert report_dir is not None
    report_json = Path(report_dir) / "branches-cleanup-report.json"
    data = json.loads(report_json.read_text())
    for entry in data:
        if entry["branch"] == current:
            assert entry["recommendation"] == "keep", f"{current} should be protected"


def test_main_is_protected():
    result = subprocess.run(
        [str(SCRIPT), "--dry-run"],
        capture_output=True, text=True
    )
    report_dir = _latest_report_dir()
    assert report_dir is not None
    report_json = Path(report_dir) / "branches-cleanup-report.json"
    data = json.loads(report_json.read_text())
    for entry in data:
        if entry["branch"] == "main":
            assert entry["recommendation"] == "keep", "main should be protected"


def test_stable_branches_protected_by_default():
    result = subprocess.run(
        [str(SCRIPT), "--dry-run"],
        capture_output=True, text=True
    )
    report_dir = _latest_report_dir()
    report_json = Path(report_dir) / "branches-cleanup-report.json"
    data = json.loads(report_json.read_text())
    stable_branches = [e for e in data if e["branch"].startswith("stable/")]
    for entry in stable_branches:
        assert entry["recommendation"] == "keep", f"{entry['branch']} should be protected by default"
