import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DIAGNOSE_SCRIPT = ROOT / "scripts" / "diagnose-v1.7-warnings.sh"


def test_diagnose_script_exists():
    if not DIAGNOSE_SCRIPT.exists():
        pytest.skip("diagnose-v1.7-warnings.sh not found")
    assert os.access(DIAGNOSE_SCRIPT, os.X_OK)


def test_diagnose_script_runs():
    if not DIAGNOSE_SCRIPT.exists():
        pytest.skip("diagnose-v1.7-warnings.sh not found")
    result = subprocess.run(
        ["bash", str(DIAGNOSE_SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0
