import importlib.util
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT_DIR / "scripts" / "validate_platform_boundaries.py"


def _load_validator():
    spec = importlib.util.spec_from_file_location("validate_platform_boundaries", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_platform_boundary_validator_knows_official_domains():
    validator = _load_validator()
    assert validator.OFFICIAL_DOMAINS == (
        "core_runtime",
        "governance",
        "federation",
        "plugin_runtime",
        "supply_chain",
        "operations",
        "security",
        "financial",
        "sovereign",
        "observability",
        "data_governance",
        "disaster_recovery",
    )


def test_platform_boundary_validator_reports_no_errors():
    validator = _load_validator()
    errors = [
        *validator.validate_structure(),
        *validator.validate_dependencies(),
        *validator.validate_shared_kernel_minimum(),
    ]
    assert not errors, errors
