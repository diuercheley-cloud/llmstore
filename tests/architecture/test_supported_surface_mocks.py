import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_supported_surface_no_mocks():
    """
    Ensures that supported/core API endpoints do not contain mock, placeholder,
    simulated, or fake data without proper exemption.

    Runs the dedicated detection script and asserts it exits with code 0.
    """
    result = subprocess.run(
        ["python3", "scripts/detect_supported_surface_mocks.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
    assert result.returncode == 0, (
        f"Mock/placeholder violations found in supported/core endpoints.\n{result.stdout}"
    )
