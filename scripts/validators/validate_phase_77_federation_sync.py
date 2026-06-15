#!/usr/bin/env python3
"""Static validation for Phase 77 sovereign federation synchronization protocol."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

REQUIRED_FILES = [
    "control_plane/app/models/operations/federation_sync.py",
    "control_plane/app/services/operations/federation_sync/hash_utils.py",
    "control_plane/app/services/operations/federation_sync/environment_registry.py",
    "control_plane/app/services/operations/federation_sync/synchronization_protocol.py",
    "control_plane/app/services/operations/federation_sync/trust_negotiation.py",
    "control_plane/app/services/operations/federation_sync/conflict_resolution.py",
    "control_plane/app/services/operations/federation_sync/replay_verifier.py",
    "control_plane/app/services/operations/federation_sync/receipts.py",
    "control_plane/app/services/operations/federation_sync/audit_events.py",
    "control_plane/app/api/operations_federation_sync_admin.py",
    "control_plane/alembic/versions/phase77_federation_sync_protocol.py",
    "docs/phases/phase_77_sovereign_federation_synchronization_protocol.md",
    "docs/operations/sovereign_federation_synchronization_protocol.md",
    "docs/operations/phase_77_federation_sync_summary.md",
    "tests/integration/operations/test_federation_sync_models.py",
    "tests/integration/operations/test_federation_hash_utils.py",
    "tests/integration/operations/test_federation_environment_registry.py",
    "tests/integration/operations/test_federation_synchronization_protocol.py",
    "tests/integration/operations/test_federation_trust_negotiation.py",
    "tests/integration/operations/test_federation_conflict_resolution.py",
    "tests/integration/operations/test_federation_replay_verifier.py",
    "tests/integration/operations/test_federation_receipts.py",
    "tests/integration/operations/test_federation_audit_events.py",
    "tests/integration/operations/test_federation_api.py",
    "tests/integration/operations/test_federation_dashboard.py",
    "tests/integration/operations/test_phase_77_validation.py",
]

REQUIRED_PATTERNS = {
    "control_plane/app/models/operations/federation_sync.py": [
        "SovereignFederationEnvironment",
        "FederationSynchronizationSession",
        "FederationSynchronizationBundle",
        "FederationTrustNegotiation",
        "FederationConflictResolution",
        "FederationSynchronizationReceipt",
        "FederationLineageLink",
        "signature_placeholder",
    ],
    "control_plane/app/api/operations_federation_sync_admin.py": [
        "/admin/operations/federation/environments",
        "/admin/operations/federation/sessions",
        "/admin/operations/federation/bundles/export",
        "/admin/operations/federation/bundles/import",
        "/admin/operations/federation/trust-negotiate",
        "/admin/operations/federation/conflicts/resolve",
        "/admin/operations/federation/lineage/",
        "/receipt",
    ],
    "control_plane/app/main.py": [
        "operations_federation_sync_admin_router",
        'operations_federation_sync_admin_router, tags=["operations-federation-sync"]',
    ],
    "control_plane/app/static/admin/index.html": [
        "Sovereign Federation Synchronization Protocol",
        "federationEnvironmentCount",
        "federationLineageVerificationStatus",
        "federationReplayVerificationStatus",
        "offline federation only",
        "placeholder trust only",
        "no real hardware-backed federation trust",
    ],
    "control_plane/app/static/portal/index.html": [
        "Sovereign Federation Synchronization Protocol",
        "portalFederationEnvironmentCount",
        "portalFederationTrustStatus",
        "offline federation only",
        "placeholder trust only",
        "no real hardware-backed federation trust",
    ],
    "docs/operations/sovereign_federation_synchronization_protocol.md": [
        "placeholder trust only",
        "no hardware-backed federation trust",
        "offline federation only",
        "No real-time synchronization",
    ],
}

PHASE_FILES = [
    "control_plane/app/models/operations/federation_sync.py",
    "control_plane/app/services/operations/federation_sync/hash_utils.py",
    "control_plane/app/services/operations/federation_sync/environment_registry.py",
    "control_plane/app/services/operations/federation_sync/synchronization_protocol.py",
    "control_plane/app/services/operations/federation_sync/trust_negotiation.py",
    "control_plane/app/services/operations/federation_sync/conflict_resolution.py",
    "control_plane/app/services/operations/federation_sync/replay_verifier.py",
    "control_plane/app/services/operations/federation_sync/receipts.py",
    "control_plane/app/services/operations/federation_sync/audit_events.py",
    "control_plane/app/api/operations_federation_sync_admin.py",
]

BANNED_PATTERNS = {
    "random": "random",
    "uuid4": "uuid4",
    "requests": "requests",
    "httpx": "httpx",
    "socket": "socket",
    "subprocess": "subprocess",
    "os.system": "os.system",
    "kubernetes real": "Kubernetes",
    "nomad real": "Nomad",
    "proxmox real": "Proxmox",
    "external ml": "external ML",
    "saas required": "SaaS required",
    "cloud required": "cloud required",
    "hardware-backed trust real": "hardware-backed trust real",
    "real-time synchronization": "real-time synchronization enabled",
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
    print("Phase 77 federation sync validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
