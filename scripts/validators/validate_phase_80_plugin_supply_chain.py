#!/usr/bin/env python3
"""Static validation for Phase 80 plugin supply-chain provenance and SBOM placeholders."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

REQUIRED_FILES = [
    "control_plane/app/models/operations/plugin_supply_chain.py",
    "control_plane/app/services/operations/plugin_supply_chain/hash_utils.py",
    "control_plane/app/services/operations/plugin_supply_chain/provenance_service.py",
    "control_plane/app/services/operations/plugin_supply_chain/sbom_placeholder.py",
    "control_plane/app/services/operations/plugin_supply_chain/dependency_governance.py",
    "control_plane/app/services/operations/plugin_supply_chain/lineage_service.py",
    "control_plane/app/services/operations/plugin_supply_chain/replay_verifier.py",
    "control_plane/app/services/operations/plugin_supply_chain/receipts.py",
    "control_plane/app/services/operations/plugin_supply_chain/audit_events.py",
    "control_plane/app/api/operations_plugin_supply_chain_admin.py",
    "control_plane/alembic/versions/phase80_plugin_supply_chain_provenance_sbom.py",
    "docs/phases/phase_80_plugin_supply_chain_provenance_sbom.md",
    "docs/operations/plugin_supply_chain_provenance_sbom.md",
    "docs/operations/phase_80_plugin_supply_chain_summary.md",
    "scripts/validators/validate_phase_80_plugin_supply_chain.py",
    "tests/integration/operations/test_plugin_supply_chain_models.py",
    "tests/integration/operations/test_plugin_supply_chain_hash_utils.py",
    "tests/integration/operations/test_plugin_supply_chain_services.py",
    "tests/integration/operations/test_plugin_supply_chain_api.py",
    "tests/integration/operations/test_plugin_supply_chain_dashboard.py",
    "tests/integration/operations/test_phase_80_validation.py",
]

REQUIRED_PATTERNS = {
    "control_plane/app/models/operations/plugin_supply_chain.py": [
        "PluginProvenanceRecord",
        "PluginSBOMPlaceholder",
        "PluginArtifactLineage",
        "DependencyGovernancePolicy",
        "PluginDependencyVerification",
        "PluginSignedArtifactPlaceholder",
        "PluginSupplyChainReceipt",
    ],
    "control_plane/app/services/operations/plugin_supply_chain/hash_utils.py": [
        "canonical_json",
        "sha256_hex",
        "compute_provenance_hash",
        "compute_sbom_hash",
        "compute_lineage_hash",
    ],
    "control_plane/app/services/operations/plugin_supply_chain/dependency_governance.py": [
        "network loaders",
        "remote package installers",
        "shell-based installers",
        "dynamic external imports",
        "unverified binary artifacts",
        "no_external_dependency_resolution",
    ],
    "control_plane/app/services/operations/plugin_supply_chain/sbom_placeholder.py": [
        "placeholder SBOM only",
        "formal_sbom",
        "deterministic metadata only",
    ],
    "control_plane/app/services/operations/plugin_supply_chain/replay_verifier.py": [
        "class PluginSupplyChainReplayVerifier",
        "compare_hashes",
    ],
    "control_plane/app/services/operations/plugin_supply_chain/lineage_service.py": [
        "class PluginArtifactLineageService",
        "verify_lineage",
    ],
    "control_plane/app/services/operations/plugin_supply_chain/receipts.py": [
        "placeholder-signature",
        "build_supply_chain_receipt",
    ],
    "control_plane/app/services/operations/plugin_supply_chain/audit_events.py": [
        "provenance_created",
        "supply_chain_receipt_created",
        "offline_compatible",
    ],
    "control_plane/app/api/operations_plugin_supply_chain_admin.py": [
        "/admin/operations/plugin-supply-chain/provenance",
        "/sbom",
        "/dependency-verify",
        "/lineage",
        "/replay-verify",
        "/sign-placeholder",
        "/receipt",
    ],
    "control_plane/app/main.py": [
        "operations_plugin_supply_chain_admin_router",
        "app.include_router(operations_plugin_supply_chain_admin_router, tags=[\"operations-plugin-supply-chain\"])",
    ],
    "control_plane/app/static/admin/index.html": [
        "Plugin Supply-Chain Provenance &amp; SBOM Placeholder Framework",
        "pluginSupplyChainProvenanceRecordCount",
        "placeholder SBOM only",
        "no real artifact signing",
        "offline-first provenance only",
    ],
    "control_plane/app/static/portal/index.html": [
        "Plugin Supply-Chain Provenance &amp; SBOM Placeholder Framework",
        "portalPluginSupplyChainProvenanceRecordCount",
        "placeholder SBOM only",
        "no real artifact signing",
        "offline-first provenance only",
    ],
    "docs/operations/plugin_supply_chain_provenance_sbom.md": [
        "Placeholder SBOM only.",
        "No real signing.",
        "No external dependency resolver.",
        "No formal supply-chain certification.",
    ],
}

PHASE_FILES = [
    "control_plane/app/models/operations/plugin_supply_chain.py",
    "control_plane/app/services/operations/plugin_supply_chain/hash_utils.py",
    "control_plane/app/services/operations/plugin_supply_chain/provenance_service.py",
    "control_plane/app/services/operations/plugin_supply_chain/sbom_placeholder.py",
    "control_plane/app/services/operations/plugin_supply_chain/dependency_governance.py",
    "control_plane/app/services/operations/plugin_supply_chain/lineage_service.py",
    "control_plane/app/services/operations/plugin_supply_chain/replay_verifier.py",
    "control_plane/app/services/operations/plugin_supply_chain/receipts.py",
    "control_plane/app/services/operations/plugin_supply_chain/audit_events.py",
    "control_plane/app/api/operations_plugin_supply_chain_admin.py",
]

BANNED_PATTERNS = {
    "uuid4 logical path": "uuid4",
    "requests import": "import requests",
    "httpx import in phase code": "import httpx",
    "socket import": "import socket",
    "subprocess import": "import subprocess",
    "subprocess from import": "from subprocess",
    "os.system call": "os.system(",
    "shell invocation": "shell=True",
    "package manager real install": "pip install",
    "npm install": "npm install",
    "apt install": "apt install",
    "real signing claim": "real signing enabled",
    "formal certification claim": "formal supply-chain certification",
    "external dependency resolver claim": "external dependency resolver enabled",
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
    print("Phase 80 plugin supply-chain validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
