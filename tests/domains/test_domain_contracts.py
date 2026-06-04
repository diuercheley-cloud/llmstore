import importlib.util
import sys
from pathlib import Path

import pytest
from app.domains.financial import FinancialDomainContract
from app.domains.governance import GovernanceDomainContract
from app.domains.operations import OperationsDomainContract
from app.domains.runtime import RuntimeDomainContract
from app.domains.sovereign import SovereignDomainContract
from app.domains.trust import TrustDomainContract

ROOT_DIR = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT_DIR / "scripts" / "validate_domain_contracts.py"


def _load_validator():
    spec = importlib.util.spec_from_file_location("validate_domain_contracts", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("contract", "expected_name"),
    [
        (RuntimeDomainContract, "RuntimeDomainContract"),
        (GovernanceDomainContract, "GovernanceDomainContract"),
        (TrustDomainContract, "TrustDomainContract"),
        (FinancialDomainContract, "FinancialDomainContract"),
        (SovereignDomainContract, "SovereignDomainContract"),
        (OperationsDomainContract, "OperationsDomainContract"),
    ],
)
def test_contracts_expose_required_fields(contract, expected_name):
    assert contract.__name__ == expected_name
    for field_name in (
        "allowed_inputs",
        "emitted_events",
        "forbidden_dependencies",
        "deterministic_requirements",
    ):
        value = getattr(contract, field_name)
        assert isinstance(value, tuple)
        assert value


def test_contracts_do_not_reference_their_own_domain_as_forbidden_dependency():
    contracts = {
        "runtime": RuntimeDomainContract,
        "governance": GovernanceDomainContract,
        "trust": TrustDomainContract,
        "financial": FinancialDomainContract,
        "sovereign": SovereignDomainContract,
        "operations": OperationsDomainContract,
    }
    for domain, contract in contracts.items():
        assert all(not dep.endswith(f".{domain}") for dep in contract.forbidden_dependencies)


def test_domain_contract_validator_passes():
    validator = _load_validator()
    failures = validator.validate_all()
    assert not failures, failures
