import os
import subprocess


def test_phase_73_validation_script():
    """Runs the phase 73 validation script and ensures it passes."""
    script_path = "scripts/validators/validate_phase_73_adapter_sandbox.py"
    assert os.path.exists(script_path)
    
    result = subprocess.run([script_path], capture_output=True, text=True)
    assert result.returncode == 0, f"Validation script failed: {result.stdout}\n{result.stderr}"
    assert "PHASE 73 VALIDATION SUCCESSFUL" in result.stdout
