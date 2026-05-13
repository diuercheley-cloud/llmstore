import json
import subprocess
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
DIAGNOSE_SCRIPT = ROOT / "scripts" / "diagnose-v1.7-warnings.sh"
CLEANUP_BASE = ROOT / "artifacts" / "v1.7-warning-cleanup"

def latest_cleanup_dir():
    if not CLEANUP_BASE.exists():
        return None
    subdirs = sorted([d for d in CLEANUP_BASE.iterdir() if d.is_dir()])
    return subdirs[-1] if subdirs else None

def test_diagnose_script_exists():
    assert DIAGNOSE_SCRIPT.exists()

def test_diagnose_script_runs():
    result = subprocess.run(["bash", str(DIAGNOSE_SCRIPT)], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0

def test_warnings_json_exists():
    d = latest_cleanup_dir()
    assert d is not None
    assert (d / "warnings.json").exists()

def test_warnings_md_exists():
    d = latest_cleanup_dir()
    assert d is not None
    assert (d / "warnings.md").exists()

def test_warnings_classification():
    d = latest_cleanup_dir()
    assert d is not None
    with open(d / "warnings.json") as f:
        data = json.load(f)
    
    for w in data["warnings"]:
        assert "classification" in w
        assert w["classification"] in ("fixable", "optional_dependency", "out_of_scope", "environment_specific", "accepted_non_blocking", "needs_review")
