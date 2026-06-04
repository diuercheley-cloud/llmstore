import os
import subprocess


def test_phase_72_validation_script():
    """Runs the phase 72 validation script and ensures it passes."""
    script_path = "scripts/validate_phase_72_remediation_execution.py"
    assert os.path.exists(script_path)
    
    result = subprocess.run([script_path], capture_output=True, text=True)
    assert result.returncode == 0, f"Validation script failed: {result.stdout}\n{result.stderr}"
    assert "PHASE 72 VALIDATION SUCCESSFUL" in result.stdout
