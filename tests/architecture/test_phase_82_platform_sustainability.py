import importlib.util
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT_DIR / "scripts" / "validate_phase_82_platform_sustainability.py"


def _load_validator():
    spec = importlib.util.spec_from_file_location("validate_phase_82_platform_sustainability", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_phase_82_validator_passes_local_checks():
    validator = _load_validator()
    errors = [
        *validator.validate_presence(),
        *validator.validate_api_registration(),
        *validator.validate_dashboards(),
        *validator.validate_forbidden_patterns(),
    ]
    assert not errors, errors
