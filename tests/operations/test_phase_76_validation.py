import subprocess
import sys


def test_phase_76_validation_script():
    result = subprocess.run(
        [sys.executable, "scripts/validate_phase_76_attestation_framework.py"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "validation passed" in result.stdout.lower()
