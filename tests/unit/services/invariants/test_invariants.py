import importlib.util
import sys
from pathlib import Path

from app.services.invariants.financial_invariants import validate_tenant_scoped_record_has_client_id
from app.services.invariants.governance_invariants import (
    validate_dry_run_does_not_mutate_persistent_state,
)
from app.services.invariants.runtime_invariants import (
    validate_receipt_has_immutable_hash,
    validate_repair_operation_emits_healing_receipt,
)
from app.services.invariants.sovereign_invariants import (
    validate_exported_sovereign_bundle_sanitized,
)
from app.services.invariants.trust_invariants import (
    validate_confidential_mode_no_plaintext,
    validate_signed_artifact_has_signature_metadata,
)

ROOT_DIR = Path(__file__).resolve().parents[4]s[3]
SCRIPT_PATH = ROOT_DIR / "scripts" / "validate_invariants.py"


def _load_validator():
    spec = importlib.util.spec_from_file_location("validate_invariants", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_receipt_must_have_immutable_hash():
    failing = validate_receipt_has_immutable_hash({})
    passing = validate_receipt_has_immutable_hash({"immutable_hash": "sha256:abc"})
    assert failing.severity == "advisory"
    assert failing.passed is False
    assert passing.passed is True


def test_confidential_mode_must_not_expose_plaintext():
    failing = validate_confidential_mode_no_plaintext(
        {"confidential_mode": True, "plaintext_fields": ("prompt",), "plaintext_payload": "raw"}
    )
    passing = validate_confidential_mode_no_plaintext(
        {"confidential_mode": True, "plaintext_fields": (), "plaintext_payload": None}
    )
    assert failing.passed is False
    assert passing.passed is True


def test_tenant_scoped_records_require_client_id():
    failing = validate_tenant_scoped_record_has_client_id({"tenant_scoped": True, "client_id": None})
    passing = validate_tenant_scoped_record_has_client_id({"tenant_scoped": True, "client_id": "client-1"})
    assert failing.passed is False
    assert passing.passed is True


def test_dry_run_must_not_mutate_persistent_state():
    failing = validate_dry_run_does_not_mutate_persistent_state(
        {"dry_run": True, "persistent_mutations": ("db.write",), "persistent_state_changed": True}
    )
    passing = validate_dry_run_does_not_mutate_persistent_state(
        {"dry_run": True, "persistent_mutations": (), "persistent_state_changed": False}
    )
    assert failing.passed is False
    assert passing.passed is True


def test_exported_sovereign_bundle_must_be_sanitized():
    failing = validate_exported_sovereign_bundle_sanitized(
        {"exported": True, "sanitized": False, "unsanitized_fields": ("secret",)}
    )
    passing = validate_exported_sovereign_bundle_sanitized(
        {"exported": True, "sanitized": True, "unsanitized_fields": ()}
    )
    assert failing.passed is False
    assert passing.passed is True


def test_signed_artifact_must_include_signature_metadata_placeholder():
    failing = validate_signed_artifact_has_signature_metadata({"signed": True, "signature_metadata": {}})
    passing = validate_signed_artifact_has_signature_metadata(
        {"signed": True, "signature_metadata": {"placeholder": "pending"}}
    )
    assert failing.passed is False
    assert passing.passed is True


def test_repair_operation_must_emit_healing_receipt():
    failing = validate_repair_operation_emits_healing_receipt({"emitted_events": (), "healing_receipt": {}})
    passing = validate_repair_operation_emits_healing_receipt(
        {
            "emitted_events": ("runtime.healing_receipt.emitted",),
            "healing_receipt": {"immutable_hash": "sha256:repair"},
        }
    )
    assert failing.passed is False
    assert passing.passed is True


def test_invariants_are_deterministic():
    payload = {"tenant_scoped": True, "client_id": "client-1"}
    first = validate_tenant_scoped_record_has_client_id(payload)
    second = validate_tenant_scoped_record_has_client_id(payload)
    assert first == second


def test_invariant_validator_passes():
    validator = _load_validator()
    failures = validator.validate_all()
    assert not failures, failures
