import subprocess
import os

def test_phase_71_validation_script():
    """Runs the phase 71 validation script and ensures it passes."""
    script_path = "scripts/validate_phase_71_remediation_planning.py"
    assert os.path.exists(script_path)
    
    result = subprocess.run([script_path], capture_output=True, text=True)
    assert result.returncode == 0, f"Validation script failed: {result.stdout}\n{result.stderr}"
    assert "PHASE 71 VALIDATION SUCCESSFUL" in result.stdout
