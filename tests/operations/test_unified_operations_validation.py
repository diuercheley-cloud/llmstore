# Owner: platform-ops
import subprocess
import sys
import pytest
from scripts.operations_validation_runner import OperationsValidationRunner

def test_all_operations_phases_unified():
    """
    Runs the unified operations validation runner.
    This replaces multiple individual phase validation scripts.
    """
    runner = OperationsValidationRunner()
    results = runner.run_all()
    
    failed_tasks = [r for r in results if r.status == "failed"]
    
    if failed_tasks:
        report = []
        for r in failed_tasks:
            report.append(f"\n❌ {r.task_name} FAILED:")
            for f in r.failures:
                report.append(f"  - {f['path']}: {f['issue']}")
        
        pytest.fail("\n".join(report))

def test_runner_execution_as_script():
    """Ensures the runner script itself can be executed without error."""
    result = subprocess.run(
        [sys.executable, "scripts/operations_validation_runner.py"],
        capture_output=True,
        text=True
    )
    # The runner might return 1 if any task fails, but here we expect 0 
    # since we just fixed the dashboard markers and patterns.
    assert result.returncode == 0, f"Runner script failed with output:\n{result.stdout}\n{result.stderr}"
