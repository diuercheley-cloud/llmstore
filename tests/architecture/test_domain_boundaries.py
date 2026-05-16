import importlib.util
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT_DIR / "scripts" / "validate_architecture_boundaries.py"


def _load_validator():
    spec = importlib.util.spec_from_file_location("validate_architecture_boundaries", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_architecture_boundary_validator_has_expected_planes():
    validator = _load_validator()
    assert set(validator.DOMAIN_BOUNDARIES) == {
        "runtime",
        "governance",
        "trust",
        "financial",
        "sovereign",
        "operations",
    }


def test_architecture_boundary_validator_reports_no_forbidden_imports():
    validator = _load_validator()
    violations = validator.find_boundary_violations()
    assert not violations, validator._format_text(violations)
