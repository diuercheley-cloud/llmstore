import subprocess
from pathlib import Path

import pytest


def test_route_surface_governance():
    """
    Ensures that the API route surface manifest is valid and compliant with governance rules.
    """
    root_dir = Path(__file__).parent.parent.parent

    # 1. Generate the manifest
    gen_result = subprocess.run(
        ["make", "generate-route-surface"], cwd=str(root_dir), capture_output=True, text=True
    )
    assert gen_result.returncode == 0, f"Manifest generation failed: {gen_result.stderr}"

    # 2. Validate the manifest
    # Note: In a real CI, this might fail if someone added a new route without classifying it.
    # For the purpose of this task, we want to make sure the TOOLING works.
    # If it fails, it provides a clear list of governance violations.
    val_result = subprocess.run(
        ["python3", "scripts/validate_route_surface.py"],
        cwd=str(root_dir),
        capture_output=True,
        text=True,
    )

    # We might want this to be non-blocking in some environments, but for architecture tests,
    # it should generally pass if the codebase is healthy.
    # Given the high number of errors currently, we'll assert success but expect it might fail
    # if the user hasn't classified all routes yet.
    if val_result.returncode != 0:
        pytest.fail(f"Route surface governance validation failed:\n{val_result.stdout}")
