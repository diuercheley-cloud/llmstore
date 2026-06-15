import subprocess
import sys
from pathlib import Path


def test_no_python_utilities_in_root():
    """Verify that no Python utility scripts are located in the repository root."""
    root_dir = Path(__file__).resolve().parents[2]

    # List of allowed .py files in root (empty for now, but could include setup.py if added later)
    allowlist = []

    python_files = list(root_dir.glob("*.py"))
    python_filenames = [f.name for f in python_files]

    unexpected_files = [f for f in python_filenames if f not in allowlist]

    assert not unexpected_files, f"Unexpected Python files found in root: {unexpected_files}"


def test_repo_layout_doc_exists():
    """Verify that docs/REPO_LAYOUT.md exists."""
    root_dir = Path(__file__).resolve().parents[2]
    layout_doc = root_dir / "docs" / "REPO_LAYOUT.md"
    assert layout_doc.exists(), "docs/REPO_LAYOUT.md is missing"


def test_moved_files_exist_in_new_locations():
    """Verify that the key files were moved to their correct locations."""
    root_dir = Path(__file__).resolve().parents[2]

    expected_locations = {
        "scripts/legacy/benchmark_model_local_runner.py": True,
        "scripts/legacy/benchmark_runner.py": True,
        "scripts/legacy/local_dr_backup.py": True,
        "scripts/backup/redact_json.py": True,
        "scripts/legacy/llm_stack_client.py": True,
        "scripts/legacy/test-max-concurrency.py": True,
        "tests/test_simulate.py": True,
    }

    for path_str, should_exist in expected_locations.items():
        path = root_dir / path_str
        assert path.exists() == should_exist, (
            f"File {path_str} existence check failed (expected {should_exist})"
        )


def test_scripts_still_executable():
    """Verify that some key scripts can still be called with --help or similar."""
    root_dir = Path(__file__).resolve().parents[2]

    # We use 'python3 scripts/...' to verify they are still runnable
    scripts_to_test = [
        "scripts/legacy/benchmark_model_local_runner.py",
        "scripts/backup/redact_json.py",
        "scripts/legacy/llm_stack_client.py",  # This is a library but should be importable
    ]

    for script_path in scripts_to_test:
        full_path = root_dir / script_path
        # Just check if it's importable or can run --help
        if "client" in script_path:
            cmd = [
                sys.executable,
                "-c",
                f"import sys; sys.path.append('scripts'); import {Path(script_path).stem}",
            ]
        else:
            cmd = [sys.executable, str(full_path), "--help"]

        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode == 0, (
            f"Script {script_path} failed to run or be imported: {result.stderr}"
        )


def test_common_sh_sets_pythonpath():
    """Verify that scripts/dev/common.sh exports PYTHONPATH including scripts/."""
    root_dir = Path(__file__).resolve().parents[2]
    common_sh = root_dir / "scripts" / "common.sh"

    cmd = f"source {common_sh} && echo $PYTHONPATH"
    result = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, check=True)

    assert "scripts" in result.stdout, (
        "PYTHONPATH does not include scripts/ directory after sourcing common.sh"
    )
