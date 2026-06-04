import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT_DIR / "scripts" / "validate_claims.py"
POLICY_PATH = ROOT_DIR / "docs" / "compliance" / "claims_policy.md"


def _load_validator():
    spec = importlib.util.spec_from_file_location("validate_claims", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_claims_policy_artifacts_exist():
    assert SCRIPT_PATH.exists()
    assert POLICY_PATH.exists()


def test_prohibited_claim_without_context_is_flagged():
    validator = _load_validator()
    failures = validator.find_claim_violations_in_text(
        "This component is military-grade and guaranteed secure.",
        ROOT_DIR / "README.md",
    )
    assert len(failures) == 2


def test_negation_and_placeholder_context_is_allowed():
    validator = _load_validator()
    failures = validator.find_claim_violations_in_text(
        "The project does not claim real hardware attestation and uses placeholder attestation metadata.",
        ROOT_DIR / "README.md",
    )
    assert not failures


def test_soc2_style_controls_are_allowed():
    validator = _load_validator()
    failures = validator.find_claim_violations_in_text(
        "The platform includes SOC2-style controls and is not certified.",
        ROOT_DIR / "README.md",
    )
    assert not failures


def test_claims_validator_passes_repository_state():
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Claims validation passed." in result.stdout
