#!/usr/bin/env python3
"""Static validation for Phase 81 reproducible build artifact verification."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

REQUIRED_FILES = [
    "control_plane/app/models/operations/reproducible_builds.py",
    "control_plane/app/services/operations/reproducible_builds/hash_utils.py",
    "control_plane/app/services/operations/reproducible_builds/reproducible_build_service.py",
    "control_plane/app/services/operations/reproducible_builds/artifact_verification.py",
    "control_plane/app/services/operations/reproducible_builds/lineage_service.py",
    "control_plane/app/services/operations/reproducible_builds/build_environment_policy.py",
    "control_plane/app/services/operations/reproducible_builds/replay_verifier.py",
    "control_plane/app/services/operations/reproducible_builds/provenance_integration.py",
    "control_plane/app/services/operations/reproducible_builds/receipts.py",
    "control_plane/app/services/operations/reproducible_builds/audit_events.py",
    "control_plane/app/api/operations_reproducible_builds_admin.py",
    "control_plane/alembic/versions/phase81_reproducible_build_artifact_verification.py",
    "docs/phases/phase_81_reproducible_build_artifact_verification.md",
    "docs/operations/reproducible_build_artifact_verification.md",
    "docs/operations/phase_81_reproducible_build_summary.md",
    "scripts/validate_phase_81_reproducible_builds.py",
    "tests/operations/test_reproducible_build_models.py",
    "tests/operations/test_reproducible_build_hash_utils.py",
    "tests/operations/test_reproducible_build_service.py",
    "tests/operations/test_artifact_verification.py",
    "tests/operations/test_source_artifact_lineage.py",
    "tests/operations/test_build_environment_policy.py",
    "tests/operations/test_artifact_replay_verifier.py",
    "tests/operations/test_reproducible_build_provenance_integration.py",
    "tests/operations/test_reproducible_build_receipts.py",
    "tests/operations/test_reproducible_build_audit_events.py",
    "tests/operations/test_reproducible_build_api.py",
    "tests/operations/test_reproducible_build_dashboard.py",
    "tests/operations/test_phase_81_validation.py",
]

REQUIRED_PATTERNS = {
    "control_plane/app/models/operations/reproducible_builds.py": [
        "ReproducibleBuildManifest",
        "ArtifactVerificationRecord",
        "SourceArtifactLineage",
        "BuildEnvironmentConstraint",
        "ReproducibilityVerificationResult",
        "ArtifactReplayVerification",
        "ReproducibleBuildReceipt",
    ],
    "control_plane/app/services/operations/reproducible_builds/hash_utils.py": [
        "canonical_json",
        "compute_build_manifest_hash",
        "compute_artifact_hash",
        "compute_lineage_hash",
        "compute_replay_hash",
    ],
    "control_plane/app/services/operations/reproducible_builds/build_environment_policy.py": [
        "external_network_allowed",
        "external_dependency_resolution_allowed",
        "dynamic dependency install",
        "shell installer",
        "remote package manager",
    ],
    "control_plane/app/services/operations/reproducible_builds/provenance_integration.py": [
        "phase80",
        "conceptual_only",
        "no real cryptographic signing",
    ],
    "control_plane/app/services/operations/reproducible_builds/receipts.py": [
        "signature_placeholder",
        "build_manifest_receipt",
        "build_artifact_receipt",
        "build_lineage_receipt",
        "build_reproducibility_receipt",
    ],
    "control_plane/app/api/operations_reproducible_builds_admin.py": [
        "/admin/operations/reproducible-builds/manifests",
        "/admin/operations/reproducible-builds/artifacts/verify",
        "/admin/operations/reproducible-builds/lineage/verify",
        "/admin/operations/reproducible-builds/replay/verify",
        "/admin/operations/reproducible-builds/environment/validate",
        "/admin/operations/reproducible-builds/dashboard",
    ],
    "control_plane/app/main.py": [
        "operations_reproducible_builds_admin_router",
        "app.include_router(operations_reproducible_builds_admin_router, tags=[\"operations-reproducible-builds\"])",
    ],
    "control_plane/app/static/admin/index.html": [
        "Reproducible Build &amp; Artifact Verification Framework",
        "reproducibleBuildManifestCount",
        "deterministic verification only",
        "no real external build execution",
        "offline-first reproducible build framework",
    ],
    "control_plane/app/static/portal/index.html": [
        "Reproducible Build &amp; Artifact Verification Framework",
        "portalReproducibleBuildManifestCount",
        "deterministic verification only",
        "no real external build execution",
        "offline-first reproducible build framework",
    ],
    "docs/operations/reproducible_build_artifact_verification.md": [
        "deterministic verification only",
        "No real external build execution.",
        "sem assinatura real",
        "sem reproducibility certification formal",
    ],
}

PHASE_FILES = [
    "control_plane/app/models/operations/reproducible_builds.py",
    "control_plane/app/services/operations/reproducible_builds/hash_utils.py",
    "control_plane/app/services/operations/reproducible_builds/reproducible_build_service.py",
    "control_plane/app/services/operations/reproducible_builds/artifact_verification.py",
    "control_plane/app/services/operations/reproducible_builds/lineage_service.py",
    "control_plane/app/services/operations/reproducible_builds/build_environment_policy.py",
    "control_plane/app/services/operations/reproducible_builds/replay_verifier.py",
    "control_plane/app/services/operations/reproducible_builds/provenance_integration.py",
    "control_plane/app/services/operations/reproducible_builds/receipts.py",
    "control_plane/app/services/operations/reproducible_builds/audit_events.py",
    "control_plane/app/api/operations_reproducible_builds_admin.py",
]

BANNED_PATTERNS = {
    "random usage": "import random",
    "uuid4 logical path": "uuid4",
    "requests import": "import requests",
    "httpx import in phase code": "import httpx",
    "socket import": "import socket",
    "subprocess import": "import subprocess",
    "subprocess from import": "from subprocess",
    "os.system call": "os.system(",
    "shell invocation": "shell=True",
    "pip install": "pip install",
    "npm install": "npm install",
    "apt install": "apt install",
    "formal certification claim": "formal reproducibility certification",
    "real signing claim": "real cryptographic signing enabled",
    "external dependency resolver claim": "external dependency resolver enabled",
    "external build claim": "real external build execution enabled",
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
    print("Phase 81 reproducible build validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
