import importlib.util
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT_DIR / "scripts" / "validate_phase_66_readiness.py"
DOC_PATH = ROOT_DIR / "docs" / "phases" / "phase_66_readiness_gate.md"


def _load_validator():
    spec = importlib.util.spec_from_file_location("validate_phase_66_readiness", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_phase_66_artifacts_exist():
    assert SCRIPT_PATH.exists()
    assert DOC_PATH.exists()


def test_phase_66_required_paths_validate():
    validator = _load_validator()
    failures = validator.validate_required_paths()
    assert not failures, failures


def test_phase_66_makefile_targets_validate():
    validator = _load_validator()
    failures = validator.validate_makefile_targets()
    assert not failures, failures


def test_phase_66_offline_validators_validate():
    validator = _load_validator()
    failures = validator.validate_offline_scripts()
    assert not failures, failures


def test_phase_66_readiness_validator_passes():
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Phase 66 readiness validation passed." in result.stdout
