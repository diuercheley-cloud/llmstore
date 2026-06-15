#!/usr/bin/env python3
"""Static validation for Phase 79 formal plugin ABI and extension runtime."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

REQUIRED_FILES = [
    "docs/rfc/README.md",
    "docs/governance/architecture_decision_governance.md",
    "docs/governance/semantic_version_governance_policy.md",
    "docs/governance/extension_compatibility_policy.md",
    "docs/governance/plugin_certification_workflow_placeholder.md",
    "docs/governance/threat_modeling_framework.md",
    "docs/governance/supply_chain_governance.md",
    "control_plane/app/models/operations/plugin_runtime.py",
    "control_plane/app/services/operations/plugin_runtime/hash_utils.py",
    "control_plane/app/services/operations/plugin_runtime/abi_contracts.py",
    "control_plane/app/services/operations/plugin_runtime/capability_boundaries.py",
    "control_plane/app/services/operations/plugin_runtime/compatibility_enforcer.py",
    "control_plane/app/services/operations/plugin_runtime/extension_loader.py",
    "control_plane/app/services/operations/plugin_runtime/isolation_policy.py",
    "control_plane/app/services/operations/plugin_runtime/lifecycle.py",
    "control_plane/app/services/operations/plugin_runtime/replay_verifier.py",
    "control_plane/app/services/operations/plugin_runtime/federation_compatibility.py",
    "control_plane/app/services/operations/plugin_runtime/receipts.py",
    "control_plane/app/services/operations/plugin_runtime/audit_events.py",
    "control_plane/app/api/operations_plugin_runtime_admin.py",
    "control_plane/alembic/versions/phase79_formal_plugin_abi_runtime.py",
    "docs/phases/phase_79_formal_plugin_abi_extension_runtime.md",
    "docs/operations/formal_plugin_abi_extension_runtime.md",
    "docs/operations/phase_79_plugin_runtime_summary.md",
    "tests/integration/operations/test_plugin_runtime_models.py",
    "tests/integration/operations/test_plugin_runtime_hash_utils.py",
    "tests/integration/operations/test_plugin_abi_contracts.py",
    "tests/integration/operations/test_plugin_capability_boundaries.py",
    "tests/integration/operations/test_plugin_runtime_compatibility_enforcer.py",
    "tests/integration/operations/test_plugin_extension_loader.py",
    "tests/integration/operations/test_plugin_isolation_policy.py",
    "tests/integration/operations/test_plugin_lifecycle.py",
    "tests/integration/operations/test_plugin_replay_verifier.py",
    "tests/integration/operations/test_plugin_federation_compatibility.py",
    "tests/integration/operations/test_plugin_runtime_receipts.py",
    "tests/integration/operations/test_plugin_runtime_audit_events.py",
    "tests/integration/operations/test_plugin_runtime_api.py",
    "tests/integration/operations/test_plugin_runtime_dashboard.py",
    "tests/integration/operations/test_phase_79_validation.py",
]

REQUIRED_PATTERNS = {
    "control_plane/app/models/operations/plugin_runtime.py": [
        "PluginABIContract",
        "PluginCapabilityBoundary",
        "PluginRuntimeCompatibilityCheck",
        "DeterministicExtensionLoadPlan",
        "PluginIsolationPolicy",
        "PluginLifecycleEvent",
        "PluginReplayVerificationResult",
        "PluginFederationCompatibility",
        "PluginRuntimeReceipt",
        "signature_placeholder",
    ],
    "control_plane/app/services/operations/plugin_runtime/abi_contracts.py": [
        "class PluginABIContractService",
        "abi_version is required",
        "placeholder_certified is not real certification",
    ],
    "control_plane/app/services/operations/plugin_runtime/capability_boundaries.py": [
        "class PluginCapabilityBoundaryService",
        "shell",
        "subprocess",
        "network",
        "dynamic_import",
    ],
    "control_plane/app/services/operations/plugin_runtime/compatibility_enforcer.py": [
        "class PluginRuntimeCompatibilityEnforcer",
        "warning",
        "blocked",
    ],
    "control_plane/app/services/operations/plugin_runtime/extension_loader.py": [
        "class DeterministicExtensionLoader",
        "deterministic load simulation only",
        "no real plugin execution",
    ],
    "control_plane/app/services/operations/plugin_runtime/replay_verifier.py": [
        "class PluginReplayVerifier",
        "compare_replay_hashes",
    ],
    "control_plane/app/services/operations/plugin_runtime/federation_compatibility.py": [
        "class PluginFederationCompatibilityService",
        "placeholder trust only",
    ],
    "control_plane/app/services/operations/plugin_runtime/receipts.py": [
        "signature_placeholder",
        "deterministic_version",
    ],
    "control_plane/app/services/operations/plugin_runtime/audit_events.py": [
        "plugin_abi_contract_created",
        "plugin_runtime_receipt_created",
        "offline_compatible",
    ],
    "control_plane/app/api/operations_plugin_runtime_admin.py": [
        "/admin/operations/plugin-runtime/contracts",
        "/admin/operations/plugin-runtime/load-plans",
        "/simulate",
        "/replay-verify",
        "/federation-compatibility",
        "/receipt",
    ],
    "control_plane/app/main.py": [
        "operations_plugin_runtime_admin_router",
        'app.include_router(operations_plugin_runtime_admin_router, tags=["operations-plugin-runtime"])',
    ],
    "control_plane/app/static/admin/index.html": [
        "Formal Plugin ABI &amp; Extension Runtime",
        "pluginAbiContractCount",
        "no real plugin execution",
        "placeholder certification only",
        "deterministic load simulation only",
    ],
    "control_plane/app/static/portal/index.html": [
        "Formal Plugin ABI &amp; Extension Runtime",
        "portalPluginAbiContractCount",
        "no real plugin execution",
        "placeholder certification only",
        "deterministic load simulation only",
    ],
    "docs/operations/formal_plugin_abi_extension_runtime.md": [
        "no real plugin execution",
        "placeholder certification only",
        "no external dynamic import",
    ],
}

PHASE_FILES = [
    "control_plane/app/models/operations/plugin_runtime.py",
    "control_plane/app/services/operations/plugin_runtime/hash_utils.py",
    "control_plane/app/services/operations/plugin_runtime/abi_contracts.py",
    "control_plane/app/services/operations/plugin_runtime/capability_boundaries.py",
    "control_plane/app/services/operations/plugin_runtime/compatibility_enforcer.py",
    "control_plane/app/services/operations/plugin_runtime/extension_loader.py",
    "control_plane/app/services/operations/plugin_runtime/isolation_policy.py",
    "control_plane/app/services/operations/plugin_runtime/lifecycle.py",
    "control_plane/app/services/operations/plugin_runtime/replay_verifier.py",
    "control_plane/app/services/operations/plugin_runtime/federation_compatibility.py",
    "control_plane/app/services/operations/plugin_runtime/receipts.py",
    "control_plane/app/services/operations/plugin_runtime/audit_events.py",
    "control_plane/app/api/operations_plugin_runtime_admin.py",
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
    "external importlib usage": "importlib",
    "kubernetes live mutation": "kubernetes mutates live clusters",
    "nomad live mutation": "nomad mutates live jobs",
    "proxmox live mutation": "proxmox mutates live nodes",
    "external ml": "external ml execution",
    "mandatory saas": "saas required",
    "mandatory cloud": "cloud required",
    "real plugin execution claim": "real plugin execution enabled",
    "real certification claim": "real certification enabled",
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
    print("Phase 79 plugin runtime validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
