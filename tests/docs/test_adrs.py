import importlib.util
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT_DIR / "scripts" / "validate_adrs.py"
ADR_ROOT = ROOT_DIR / "docs" / "adr"


def _load_validator():
    spec = importlib.util.spec_from_file_location("validate_adrs", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_adr_directory_exists():
    assert ADR_ROOT.exists()
    assert (ADR_ROOT / "README.md").exists()


def test_all_required_adr_files_exist():
    validator = _load_validator()
    failures = validator.validate_required_files()
    assert not failures, failures


def test_all_adrs_have_required_sections():
    validator = _load_validator()
    failures = validator.validate_sections()
    assert not failures, failures


def test_adrs_do_not_contain_prohibited_claims():
    validator = _load_validator()
    failures = validator.validate_prohibited_claims()
    assert not failures, failures


def test_adr_validator_passes():
    validator = _load_validator()
    failures = validator.validate_all()
    assert not failures, failures
