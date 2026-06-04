import subprocess
import sys


def test_phase_75_validation_script():
    result = subprocess.run(
        [sys.executable, "scripts/validate_phase_75_adapter_promotion.py"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "SUCCESS" in result.stdout
