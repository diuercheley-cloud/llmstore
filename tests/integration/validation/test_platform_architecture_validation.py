import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]
SCRIPT_PATH = ROOT_DIR / "scripts" / "validate_platform_architecture.py"


def _load_validator():
    spec = importlib.util.spec_from_file_location("validate_platform_architecture", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_platform_architecture_validation_script_exists():
    assert SCRIPT_PATH.exists()


def test_validation_targets_include_expected_scripts():
    validator = _load_validator()
    targets = {target.script_path.name for target in validator.VALIDATION_TARGETS}
    assert targets == {
        "validate_architecture_boundaries.py",
        "validate_runtime_contracts.py",
        "validate_domain_contracts.py",
        "validate_adrs.py",
        "validate_invariants.py",
    }


def test_run_target_skips_missing_script():
    validator = _load_validator()
    missing_target = validator.ValidationTarget(
        name="Missing",
        script_path=ROOT_DIR / "scripts" / "does_not_exist.py",
    )
    status, exit_code, output = validator.run_target(missing_target)
    assert status == "SKIP"
    assert exit_code == 0
    assert "not available" in output


def test_platform_architecture_validation_runner_passes():
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Platform architecture validation suite" in result.stdout
    assert "Platform architecture validation passed." in result.stdout
