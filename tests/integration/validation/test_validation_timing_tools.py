import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]


def test_measure_validation_targets_script_exists():
    script = ROOT_DIR / "scripts" / "measure_validation_targets.py"
    assert script.exists()


def test_measure_validation_targets_help():
    script = ROOT_DIR / "scripts" / "measure_validation_targets.py"
    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "usage:" in result.stdout or "usage:" in result.stderr


def test_measure_validation_targets_json_output():
    script = ROOT_DIR / "scripts" / "measure_validation_targets.py"
    result = subprocess.run(
        [
            sys.executable, str(script),
            "--targets", "validate-makefile-governance",
            "--json",
            "--timeout", "60",
        ],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0
    assert "validate-makefile-governance" in result.stdout


def test_list_slow_tests_script_exists():
    script = ROOT_DIR / "scripts" / "list_slow_tests.py"
    assert script.exists()


def test_list_slow_tests_help():
    script = ROOT_DIR / "scripts" / "list_slow_tests.py"
    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "usage:" in result.stdout or "usage:" in result.stderr


def test_list_slow_tests_can_run_on_small_dir():
    script = ROOT_DIR / "scripts" / "list_slow_tests.py"
    result = subprocess.run(
        [
            sys.executable, str(script),
            "--test-dir", "tests/integration/build",
            "--top-n", "5",
            "--timeout", "60",
        ],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0


def test_scripts_import_without_error():
    import importlib.util
    for script_name in ("measure_validation_targets.py", "list_slow_tests.py"):
        path = ROOT_DIR / "scripts" / script_name
        spec = importlib.util.spec_from_file_location(script_name.replace(".py", ""), path)
        assert spec is not None, f"Failed to load spec for {script_name}"
