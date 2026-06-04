import subprocess
from pathlib import Path


def test_dr_test_local_help():
    """
    Simple check that the DR test script exists and can show help.
    """
    root_dir = Path(__file__).resolve().parents[1]
    dr_script = root_dir / "scripts" / "dr-test-local.sh"
    
    result = subprocess.run(
        [str(dr_script), "--help"],
        capture_output=True,
        text=True,
        cwd=str(root_dir)
    )
    
    assert result.returncode == 0
    assert "Uso: ./scripts/dr-test-local.sh" in result.stdout

def test_dr_test_local_report_path_config():
    """
    Checks that the script points to the correct artifacts directory.
    """
    root_dir = Path(__file__).resolve().parents[1]
    dr_script = root_dir / "scripts" / "dr-test-local.sh"
    
    content = dr_script.read_text()
    assert 'REPORT_ROOT="${ROOT_DIR}/artifacts/dr-tests"' in content
