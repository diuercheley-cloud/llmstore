#!/usr/bin/env python3
"""Validate lightweight advisory invariants framework structure and behavior."""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTROL_PLANE_ROOT = REPO_ROOT / "control_plane"
if str(CONTROL_PLANE_ROOT) not in sys.path:
    sys.path.insert(0, str(CONTROL_PLANE_ROOT))

DOC_PATH = REPO_ROOT / "docs" / "architecture" / "invariants.md"

REQUIRED_FILES = (
    "control_plane/app/services/invariants/__init__.py",
    "control_plane/app/services/invariants/base.py",
    "control_plane/app/services/invariants/runtime_invariants.py",
    "control_plane/app/services/invariants/governance_invariants.py",
    "control_plane/app/services/invariants/trust_invariants.py",
    "control_plane/app/services/invariants/financial_invariants.py",
    "control_plane/app/services/invariants/sovereign_invariants.py",
    "tests/services/invariants/test_invariants.py",
    "docs/architecture/invariants.md",
)

REQUIRED_DOC_FRAGMENTS = (
    "# Platform Invariants",
    "deterministica",
    "advisory",
    "offline-first",
    "immutable_hash",
    "plaintext",
    "client_id",
    "dry_run",
    "sanitized",
    "signature metadata placeholder",
    "healing receipt",
)

FUNCTION_SPECS = (
    (
        "app.services.invariants.runtime_invariants",
        "validate_receipt_has_immutable_hash",
        {"immutable_hash": "sha256:abc"},
    ),
    (
        "app.services.invariants.runtime_invariants",
        "validate_repair_operation_emits_healing_receipt",
        {
            "emitted_events": ("runtime.healing_receipt.emitted",),
            "healing_receipt": {"immutable_hash": "sha256:healing"},
        },
    ),
    (
        "app.services.invariants.governance_invariants",
        "validate_dry_run_does_not_mutate_persistent_state",
        {"dry_run": True, "persistent_mutations": (), "persistent_state_changed": False},
    ),
    (
        "app.services.invariants.trust_invariants",
        "validate_confidential_mode_no_plaintext",
        {"confidential_mode": True, "plaintext_fields": (), "plaintext_payload": None},
    ),
    (
        "app.services.invariants.trust_invariants",
        "validate_signed_artifact_has_signature_metadata",
        {"signed": True, "signature_metadata": {"placeholder": "pending"}},
    ),
    (
        "app.services.invariants.financial_invariants",
        "validate_tenant_scoped_record_has_client_id",
        {"tenant_scoped": True, "client_id": "client-123"},
    ),
    (
        "app.services.invariants.sovereign_invariants",
        "validate_exported_sovereign_bundle_sanitized",
        {"exported": True, "sanitized": True, "unsanitized_fields": ()},
    ),
)


def validate_required_files() -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    for relative_path in REQUIRED_FILES:
        path = REPO_ROOT / relative_path
        if not path.exists():
            failures.append({"path": relative_path, "issue": "missing file"})
    return failures


def validate_docs() -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    if not DOC_PATH.exists():
        return [{"path": str(DOC_PATH.relative_to(REPO_ROOT)), "issue": "missing file"}]
    content = DOC_PATH.read_text(encoding="utf-8")
    for fragment in REQUIRED_DOC_FRAGMENTS:
        if fragment not in content:
            failures.append({"path": str(DOC_PATH.relative_to(REPO_ROOT)), "issue": f"missing fragment: {fragment}"})
    return failures


def validate_behaviors() -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    for module_name, function_name, payload in FUNCTION_SPECS:
        module = importlib.import_module(module_name)
        function = getattr(module, function_name, None)
        if function is None:
            failures.append({"path": module_name, "issue": f"missing function {function_name}"})
            continue
        result = function(payload)
        if getattr(result, "severity", None) != "advisory":
            failures.append({"path": f"{module_name}.{function_name}", "issue": "severity must be advisory"})
        if getattr(result, "passed", None) is not True:
            failures.append({"path": f"{module_name}.{function_name}", "issue": "expected passing sample payload"})
    return failures


def validate_all() -> list[dict[str, str]]:
    return [*validate_required_files(), *validate_docs(), *validate_behaviors()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit failures as JSON.")
    args = parser.parse_args()

    failures = validate_all()
    if args.json:
        print(json.dumps(failures, indent=2, sort_keys=True))
    elif failures:
        print("Invariant validation failed:")
        for failure in failures:
            print(f"- {failure['path']}: {failure['issue']}")
    else:
        print("Invariant validation passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

