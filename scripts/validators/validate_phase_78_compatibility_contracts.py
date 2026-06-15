#!/usr/bin/env python3
"""Static validation for Phase 78 compatibility contracts and version negotiation."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

REQUIRED_FILES = [
    "control_plane/app/models/operations/compatibility_contracts.py",
    "control_plane/app/services/operations/compatibility_contracts/hash_utils.py",
    "control_plane/app/services/operations/compatibility_contracts/semantic_versioning.py",
    "control_plane/app/services/operations/compatibility_contracts/compatibility_matrix.py",
    "control_plane/app/services/operations/compatibility_contracts/version_negotiation.py",
    "control_plane/app/services/operations/compatibility_contracts/capability_negotiation.py",
    "control_plane/app/services/operations/compatibility_contracts/deprecation_lifecycle.py",
    "control_plane/app/services/operations/compatibility_contracts/verification.py",
    "control_plane/app/services/operations/compatibility_contracts/receipts.py",
    "control_plane/app/services/operations/compatibility_contracts/audit_events.py",
    "control_plane/app/api/operations_compatibility_admin.py",
    "control_plane/alembic/versions/phase78_compatibility_contracts.py",
    "docs/phases/phase_78_compatibility_contracts_and_version_negotiation.md",
    "docs/operations/compatibility_contracts_and_version_negotiation.md",
    "docs/operations/phase_78_compatibility_summary.md",
    "tests/integration/operations/test_compatibility_models.py",
    "tests/integration/operations/test_compatibility_hash_utils.py",
    "tests/integration/operations/test_semantic_versioning.py",
    "tests/integration/operations/test_compatibility_matrix.py",
    "tests/integration/operations/test_version_negotiation.py",
    "tests/integration/operations/test_capability_negotiation.py",
    "tests/integration/operations/test_deprecation_lifecycle.py",
    "tests/integration/operations/test_compatibility_verification.py",
    "tests/integration/operations/test_compatibility_receipts.py",
    "tests/integration/operations/test_compatibility_audit_events.py",
    "tests/integration/operations/test_compatibility_api.py",
    "tests/integration/operations/test_compatibility_dashboard.py",
    "tests/integration/operations/test_phase_78_validation.py",
]

REQUIRED_PATTERNS = {
    "control_plane/app/models/operations/compatibility_contracts.py": [
        "CompatibilityContract",
        "CompatibilityMatrix",
        "VersionNegotiationSession",
        "CapabilityNegotiation",
        "FeatureCompatibilityFlag",
        "DeprecationLifecycle",
        "CompatibilityVerificationResult",
        "CompatibilityReceipt",
        "signature_placeholder",
    ],
    "control_plane/app/services/operations/compatibility_contracts/semantic_versioning.py": [
        "class SemanticVersioningService",
        "parse_version",
        "compare_versions",
        "is_backward_compatible",
        "is_forward_compatible",
        "is_bidirectional_compatible",
    ],
    "control_plane/app/services/operations/compatibility_contracts/compatibility_matrix.py": [
        "class CompatibilityMatrixService",
        "build_matrix",
        "replay_safe",
    ],
    "control_plane/app/services/operations/compatibility_contracts/version_negotiation.py": [
        "class VersionNegotiationService",
        "negotiate",
        "replay_verifiable",
    ],
    "control_plane/app/services/operations/compatibility_contracts/capability_negotiation.py": [
        "class CapabilityNegotiationService",
        "shell",
        "subprocess",
        "network",
        "hardware_attestation_real",
    ],
    "control_plane/app/services/operations/compatibility_contracts/deprecation_lifecycle.py": [
        "class DeprecationLifecycleService",
        "replacement_contract is required",
    ],
    "control_plane/app/services/operations/compatibility_contracts/receipts.py": [
        "signature_placeholder",
        "deterministic_version",
    ],
    "control_plane/app/api/operations_compatibility_admin.py": [
        "/admin/operations/compatibility/contracts",
        "/admin/operations/compatibility/matrix",
        "/admin/operations/compatibility/negotiate",
        "/admin/operations/compatibility/capabilities/negotiate",
        "/admin/operations/compatibility/deprecations",
        "/receipt",
    ],
    "control_plane/app/main.py": [
        "operations_compatibility_admin_router",
        'app.include_router(operations_compatibility_admin_router, tags=["operations-compatibility"])',
    ],
    "control_plane/app/static/admin/index.html": [
        "Compatibility Contracts & Version Negotiation",
        "compatibilityContractCount",
        "deterministic compatibility only",
        "no real hardware-backed compatibility trust",
    ],
    "control_plane/app/static/portal/index.html": [
        "Compatibility Contracts & Version Negotiation",
        "portalCompatibilityContractCount",
        "deterministic compatibility only",
        "no real hardware-backed compatibility trust",
    ],
    "docs/operations/compatibility_contracts_and_version_negotiation.md": [
        "deterministic compatibility only",
        "no real hardware-backed compatibility trust",
        "no external dependency resolver",
    ],
}

PHASE_FILES = [
    "control_plane/app/models/operations/compatibility_contracts.py",
    "control_plane/app/services/operations/compatibility_contracts/hash_utils.py",
    "control_plane/app/services/operations/compatibility_contracts/semantic_versioning.py",
    "control_plane/app/services/operations/compatibility_contracts/compatibility_matrix.py",
    "control_plane/app/services/operations/compatibility_contracts/version_negotiation.py",
    "control_plane/app/services/operations/compatibility_contracts/capability_negotiation.py",
    "control_plane/app/services/operations/compatibility_contracts/deprecation_lifecycle.py",
    "control_plane/app/services/operations/compatibility_contracts/verification.py",
    "control_plane/app/services/operations/compatibility_contracts/receipts.py",
    "control_plane/app/services/operations/compatibility_contracts/audit_events.py",
    "control_plane/app/api/operations_compatibility_admin.py",
]

BANNED_PATTERNS = {
    "random import": "import random",
    "uuid4 logical path": "uuid4",
    "requests import": "import requests",
    "httpx import": "import httpx",
    "socket import": "import socket",
    "subprocess import": "import subprocess",
    "subprocess from import": "from subprocess",
    "os.system call": "os.system(",
    "real kubernetes mutation": "kubernetes mutates live clusters",
    "real nomad mutation": "nomad mutates live jobs",
    "real proxmox mutation": "proxmox mutates live nodes",
    "external dependency resolver": "dependency resolver externo habilitado",
    "external ml": "external ml execution",
    "mandatory saas": "saas required",
    "mandatory cloud": "cloud required",
    "hardware backed claim": "hardware-backed compatibility trust enabled",
}


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
    print("Phase 78 compatibility contracts validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
