#!/usr/bin/env python3
"""Static validation for Phase 76 sovereign execution attestation framework."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

REQUIRED_FILES = [
    "control_plane/app/models/operations/attestation_framework.py",
    "control_plane/app/services/operations/attestation_framework/hash_utils.py",
    "control_plane/app/services/operations/attestation_framework/attestation_service.py",
    "control_plane/app/services/operations/attestation_framework/federation_bundle.py",
    "control_plane/app/services/operations/attestation_framework/trust_policy_engine.py",
    "control_plane/app/services/operations/attestation_framework/replay_verifier.py",
    "control_plane/app/services/operations/attestation_framework/receipts.py",
    "control_plane/app/services/operations/attestation_framework/audit_events.py",
    "control_plane/app/api/operations_attestation_admin.py",
    "control_plane/alembic/versions/phase76_attestation_framework.py",
    "docs/phases/phase_76_sovereign_execution_attestation_framework.md",
    "docs/operations/sovereign_execution_attestation_framework.md",
    "docs/operations/phase_76_attestation_framework_summary.md",
    "tests/integration/operations/test_attestation_framework_models.py",
    "tests/integration/operations/test_attestation_hash_utils.py",
    "tests/integration/operations/test_attestation_service.py",
    "tests/integration/operations/test_attestation_federation_bundle.py",
    "tests/integration/operations/test_attestation_trust_policy_engine.py",
    "tests/integration/operations/test_attestation_replay_verifier.py",
    "tests/integration/operations/test_attestation_receipts.py",
    "tests/integration/operations/test_attestation_audit_events.py",
    "tests/integration/operations/test_attestation_api.py",
    "tests/integration/operations/test_attestation_dashboard.py",
    "tests/integration/operations/test_phase_76_validation.py",
]

BANNED_PATTERNS = {
    "requests/": "requests.",
    "httpx/": "httpx.",
    "socket": "socket",
    "subprocess": "subprocess",
    "os.system": "os.system",
    "random": "random",
    "uuid4": "uuid4",
    "TPM": "TPM",
    "SGX": "SGX real",
    "SEV": "SEV real",
    "Kubernetes": "Kubernetes",
    "Nomad": "Nomad",
    "Proxmox": "Proxmox",
    "external ML": "external ML",
    "cloud required": "cloud required",
    "hardware-backed trust real": "hardware-backed trust real",
    "confidential computing real": "confidential computing real",
}

REQUIRED_PATTERNS = {
    "control_plane/app/models/operations/attestation_framework.py": [
        "SovereignExecutionAttestation",
        "AttestationTrustPolicy",
        "AttestationFederationBundle",
        "AttestationVerificationResult",
        "AttestationReceipt",
        "AttestationChainLink",
        "replay_verifiable",
        "offline_verifiable",
        "signature_placeholder",
    ],
    "control_plane/app/api/operations_attestation_admin.py": [
        "/attestations",
        "/attestation-bundles/import",
        "/attestation-chains/",
        "/receipt",
    ],
    "control_plane/app/main.py": [
        "operations_attestation_admin_router",
        'prefix="/admin/operations"',
    ],
    "control_plane/app/static/admin/index.html": [
        "Sovereign Execution Attestation Framework",
        "attestationFrameworkCount",
        "placeholder attestation only",
        "no hardware-backed trust implemented",
        "chain integrity status",
    ],
    "control_plane/app/static/portal/index.html": [
        "Sovereign Execution Attestation Framework",
        "portalAttestationCount",
        "placeholder attestation only",
        "no hardware-backed trust implemented",
    ],
    "docs/operations/sovereign_execution_attestation_framework.md": [
        "placeholder attestation only",
        "no hardware-backed trust",
        "no confidential computing",
        "offline-first",
    ],
}

PHASE_FILES = [
    "control_plane/app/models/operations/attestation_framework.py",
    "control_plane/app/services/operations/attestation_framework/hash_utils.py",
    "control_plane/app/services/operations/attestation_framework/attestation_service.py",
    "control_plane/app/services/operations/attestation_framework/federation_bundle.py",
    "control_plane/app/services/operations/attestation_framework/trust_policy_engine.py",
    "control_plane/app/services/operations/attestation_framework/replay_verifier.py",
    "control_plane/app/services/operations/attestation_framework/receipts.py",
    "control_plane/app/services/operations/attestation_framework/audit_events.py",
    "control_plane/app/api/operations_attestation_admin.py",
]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def validate() -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    for relative_path in REQUIRED_FILES:
        if not (REPO_ROOT / relative_path).exists():
            failures.append({"path": relative_path, "issue": "missing required file"})
    for relative_path, patterns in REQUIRED_PATTERNS.items():
        if not (REPO_ROOT / relative_path).exists():
            continue
        content = _read(relative_path)
        for pattern in patterns:
            if pattern not in content:
                failures.append({"path": relative_path, "issue": f"missing pattern: {pattern}"})
    for relative_path in PHASE_FILES:
        if not (REPO_ROOT / relative_path).exists():
            continue
        content = _read(relative_path)
        for issue, pattern in BANNED_PATTERNS.items():
            if pattern in content:
                failures.append({"path": relative_path, "issue": f"banned pattern found: {issue}"})
    return failures


def main() -> int:
    failures = validate()
    if failures:
        print(json.dumps(failures, indent=2, sort_keys=True))
        return 1
    print("Phase 76 attestation framework validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
