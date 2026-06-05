#!/usr/bin/env python3
# Owner: platform-ops
"""
Operations Validation Runner — Unified interface for technical phase validation.

This script consolidates all phase-specific validators into a single declarative runner.
It handles file existence, content patterns, forbidden patterns (hardening), 
and dashboard markers.

To add a new validation:
1. Open this file and find the `_load_tasks` method.
2. Add a new `ValidationTask` to the `self.tasks` list:
   self.tasks.append(ValidationTask(
       name="My New Feature",
       phase=99,
       required_files=["path/to/file.py"],
       required_patterns={"path/to/file.py": ["required_pattern"]},
       forbidden_patterns={"path/to/file.py": {"hardening label": "forbidden_regex"}}
   ))
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent

@dataclass
class ValidationTask:
    name: str
    phase: int
    required_files: list[str] = field(default_factory=list)
    required_patterns: dict[str, list[str]] = field(default_factory=dict)
    forbidden_patterns: dict[str, dict[str, str]] = field(default_factory=dict)
    is_obsolete: bool = False
    is_skipped: bool = False

@dataclass
class ValidationResult:
    task_name: str
    status: str  # passed, failed, skipped, obsolete
    failures: list[dict[str, str]] = field(default_factory=list)

class OperationsValidationRunner:
    def __init__(self):
        self.tasks: list[ValidationTask] = []
        self._load_tasks()

    def _load_tasks(self):
        """Register validations for all phases."""
        
        # Phase 73: Controlled Adapter Sandbox
        self.tasks.append(ValidationTask(
            name="Controlled Adapter Sandbox",
            phase=73,
            required_files=[
                "control_plane/app/models/operations/adapter_sandbox.py",
                "control_plane/app/services/operations/adapter_sandbox/contracts.py",
                "control_plane/app/api/operations_adapter_sandbox_admin.py",
            ],
            required_patterns={
                "control_plane/app/api/operations_adapter_sandbox_admin.py": ["router = APIRouter", "/manifests", "/runs/simulate"],
                "control_plane/app/static/admin/index.html": ["Controlled Adapter Sandbox", "sandbox simulation only"],
                "control_plane/app/static/portal/index.html": ["Controlled Adapter Sandbox", "sandbox simulation only"],
            },
            forbidden_patterns={
                "control_plane/app/services/operations/adapter_sandbox/simulation_runner.py": {
                    "external network": "requests\\.|httpx\\.|urllib|socket\\.",
                    "subprocess": "subprocess\\.|os\\.system",
                }
            }
        ))

        # Phase 74: Signed Adapter Registry
        self.tasks.append(ValidationTask(
            name="Signed Adapter Registry",
            phase=74,
            required_files=[
                "control_plane/app/models/operations/adapter_registry.py",
                "control_plane/app/api/operations_adapter_registry_admin.py",
            ],
            required_patterns={
                "control_plane/app/models/operations/adapter_registry.py": ["SignedAdapterRegistryEntry", "signature_placeholder", "manifest_hash"],
                "control_plane/app/static/admin/index.html": ["Signed Adapter Registry", "adapterRegistryCount", "adapterRegistryApprovedCount"],
            }
        ))

        # Phase 76: Attestation Framework
        self.tasks.append(ValidationTask(
            name="Attestation Framework",
            phase=76,
            required_files=[
                "control_plane/app/models/operations/attestation_framework.py",
                "control_plane/app/api/operations_attestation_admin.py",
            ],
            required_patterns={
                "control_plane/app/models/operations/attestation_framework.py": ["SovereignExecutionAttestation", "signature_placeholder"],
                "control_plane/app/static/admin/index.html": ["Sovereign Execution Attestation Framework", "chain integrity status"],
            }
        ))

        # Phase 77: Federation Sync
        self.tasks.append(ValidationTask(
            name="Federation Sync",
            phase=77,
            required_files=[
                "control_plane/app/models/operations/federation_sync.py",
                "control_plane/app/api/operations_federation_sync_admin.py",
            ],
            required_patterns={
                "control_plane/app/models/operations/federation_sync.py": ["SovereignFederationEnvironment", "signature_placeholder"],
                "control_plane/app/static/admin/index.html": ["Sovereign Federation Synchronization Protocol", "federationLineageVerificationStatus"],
            }
        ))

        # Phase 78: Compatibility Contracts
        self.tasks.append(ValidationTask(
            name="Compatibility Contracts",
            phase=78,
            required_files=[
                "control_plane/app/models/operations/compatibility_contracts.py",
                "control_plane/app/api/operations_compatibility_admin.py",
            ],
            required_patterns={
                "control_plane/app/models/operations/compatibility_contracts.py": ["CompatibilityContract", "signature_placeholder"],
                "control_plane/app/static/admin/index.html": ["Compatibility Contracts & Version Negotiation"],
            }
        ))

        # Phase 79: Plugin Runtime
        self.tasks.append(ValidationTask(
            name="Plugin Runtime",
            phase=79,
            required_files=[
                "control_plane/app/models/operations/plugin_runtime.py",
                "control_plane/app/api/operations_plugin_runtime_admin.py",
            ],
            required_patterns={
                "control_plane/app/models/operations/plugin_runtime.py": ["PluginABIContract", "signature_placeholder"],
                "control_plane/app/static/admin/index.html": ["Formal Plugin ABI &amp; Extension Runtime"],
            }
        ))

        # Phase 81: Reproducible Builds
        self.tasks.append(ValidationTask(
            name="Reproducible Builds",
            phase=81,
            required_files=[
                "control_plane/app/models/operations/reproducible_builds.py",
                "control_plane/app/services/operations/reproducible_builds/receipts.py",
            ],
            required_patterns={
                "control_plane/app/models/operations/reproducible_builds.py": ["ReproducibleBuildManifest"],
                "control_plane/app/services/operations/reproducible_builds/receipts.py": ["signature_placeholder"],
                "control_plane/app/static/admin/index.html": ["Reproducible Build &amp; Artifact Verification Framework"],
            }
        ))

        # Example of obsolete validation
        self.tasks.append(ValidationTask(
            name="Legacy Readiness (Phase 66)",
            phase=66,
            is_obsolete=True
        ))

    def run_all(self) -> list[ValidationResult]:
        results = []
        for task in self.tasks:
            results.append(self.run_task(task))
        return results

    def run_task(self, task: ValidationTask) -> ValidationResult:
        if task.is_obsolete:
            return ValidationResult(task.name, "obsolete")
        if task.is_skipped:
            return ValidationResult(task.name, "skipped")

        failures = []

        # Check required files
        for rel_path in task.required_files:
            if not (REPO_ROOT / rel_path).exists():
                failures.append({"path": rel_path, "issue": "missing required file"})

        # Check required patterns
        for rel_path, patterns in task.required_patterns.items():
            full_path = REPO_ROOT / rel_path
            if not full_path.exists():
                # Already reported as missing if in required_files, but we skip pattern check
                continue
            content = full_path.read_text(encoding="utf-8")
            for p in patterns:
                if not re.search(p, content):
                    failures.append({"path": rel_path, "issue": f"missing required pattern: {p}"})

        # Check forbidden patterns (Hardening)
        for rel_path, patterns in task.forbidden_patterns.items():
            full_path = REPO_ROOT / rel_path
            if not full_path.exists():
                continue
            content = full_path.read_text(encoding="utf-8")
            for label, p in patterns.items():
                if re.search(p, content):
                    failures.append({"path": rel_path, "issue": f"FORBIDDEN pattern found: {label} ({p})"})

        status = "failed" if failures else "passed"
        return ValidationResult(task.name, status, failures)

    def report(self, results: list[ValidationResult]):
        print("\n=== Operations Validation Report ===\n")
        exit_code = 0
        for r in results:
            icon = {"passed": "✅", "failed": "❌", "skipped": "🟡", "obsolete": "⚪"}.get(r.status, "❓")
            print(f"{icon} {r.task_name: <35} [{r.status.upper()}]")
            if r.status == "failed":
                exit_code = 1
                for f in r.failures:
                    print(f"   - {f['path']}: {f['issue']}")
        
        print(f"\nSummary: {len([r for r in results if r.status == 'passed'])} passed, "
              f"{len([r for r in results if r.status == 'failed'])} failed, "
              f"{len([r for r in results if r.status == 'obsolete'])} obsolete.")
        return exit_code

def main():
    runner = OperationsValidationRunner()
    results = runner.run_all()
    sys.exit(runner.report(results))

if __name__ == "__main__":
    main()
