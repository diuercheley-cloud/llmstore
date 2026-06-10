#!/usr/bin/env python3
"""Validate Phase 82 platform sustainability artifacts."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

REQUIRED_DOCS = [
    "docs/architecture/platform_modularization.md",
    "docs/architecture/bounded_contexts.md",
    "docs/architecture/dependency_direction_rules.md",
    "docs/architecture/public_internal_api_boundaries.md",
    "docs/architecture/shared_kernel_policy.md",
    "docs/governance/deterministic_policy_engine.md",
    "docs/governance/policy_dsl.md",
    "docs/governance/data_governance.md",
    "docs/governance/human_governance_workflows.md",
    "docs/operations/deterministic_event_architecture.md",
    "docs/operations/sovereign_observability.md",
    "docs/operations/sovereign_disaster_recovery.md",
    "docs/runtime/real_execution_readiness.md",
    "docs/security/real_crypto_readiness.md",
    "docs/plugins/real_plugin_runtime_readiness.md",
]

REQUIRED_PATHS = [
    "control_plane/app/models/governance/policy_engine.py",
    "control_plane/app/services/governance/policy_engine",
    "control_plane/app/models/operations/deterministic_events.py",
    "control_plane/app/services/operations/events",
    "control_plane/app/models/operations/sovereign_observability.py",
    "control_plane/app/services/operations/observability",
    "control_plane/app/models/governance/data_governance.py",
    "control_plane/app/services/governance/data_governance",
    "control_plane/app/models/governance/human_governance.py",
    "control_plane/app/services/governance/human_governance",
    "control_plane/app/models/operations/disaster_recovery.py",
    "control_plane/app/services/operations/disaster_recovery",
    "control_plane/app/api/governance_policy_engine_admin.py",
    "scripts/validators/validate_platform_boundaries.py",
]

DOMAIN_NAMES = [
    "core_runtime",
    "governance",
    "federation",
    "plugin_runtime",
    "supply_chain",
    "operations",
    "security",
    "financial",
    "sovereign",
    "observability",
    "data_governance",
    "disaster_recovery",
]

PROHIBITED_TOKENS = ["eval(", "exec(", "subprocess.", "os.system("]
SOFT_PROHIBITED_MARKERS = ["requests", "httpx", "socket", "kubernetes", "nomad", "proxmox"]
SCAN_PATHS = [
    "control_plane/app/models/governance",
    "control_plane/app/models/operations/deterministic_events.py",
    "control_plane/app/models/operations/sovereign_observability.py",
    "control_plane/app/models/operations/disaster_recovery.py",
    "control_plane/app/services/governance/policy_engine",
    "control_plane/app/services/governance/data_governance",
    "control_plane/app/services/governance/human_governance",
    "control_plane/app/services/operations/events",
    "control_plane/app/services/operations/observability",
    "control_plane/app/services/operations/disaster_recovery",
    "control_plane/app/api/governance_policy_engine_admin.py",
]


def _iter_files(path_str: str) -> list[Path]:
    path = REPO_ROOT / path_str
    if path.is_file():
        return [path]
    if path.is_dir():
        return sorted(
            item
            for item in path.rglob("*")
            if item.is_file() and "__pycache__" not in item.parts and item.suffix in {".py", ".md", ".html"}
        )
    return []


def validate_presence() -> list[str]:
    errors = []
    for relative in REQUIRED_DOCS + REQUIRED_PATHS:
        if not (REPO_ROOT / relative).exists():
            errors.append(f"missing required artifact: {relative}")
    for domain in DOMAIN_NAMES:
        base = REPO_ROOT / "control_plane/app/domains" / domain
        for required in ("contracts.py", "events.py", "schemas.py", "ownership.md"):
            if not (base / required).exists():
                errors.append(f"missing domain boundary artifact: {base / required}")
    return errors


def validate_api_registration() -> list[str]:
    main_text = (REPO_ROOT / "control_plane/app/main.py").read_text(encoding="utf-8")
    return [] if "governance_policy_engine_admin_router" in main_text else ["policy engine router not registered in main.py"]


def validate_dashboards() -> list[str]:
    errors = []
    required_labels = [
        "Platform Boundary Enforcement",
        "Deterministic Policy Engine",
        "Deterministic Event Architecture",
        "Sovereign Observability",
        "Data Governance",
        "Human Governance Workflows",
        "Sovereign Disaster Recovery",
        "offline-first",
        "no real external execution",
        "no formal certification claims",
    ]
    
    # Admin part: check hub or legacy
    admin_files = [
        "control_plane/app/static/admin/index.html",
        "control_plane/app/static/admin/index.legacy.html"
    ]
    admin_content = ""
    for f in admin_files:
        if (REPO_ROOT / f).exists():
            admin_content += (REPO_ROOT / f).read_text(encoding="utf-8").lower()
    
    for label in required_labels:
        if label.lower() not in admin_content:
            errors.append(f"admin dashboards missing label '{label}' (checked hub and legacy)")
            
    # Portal part: check hub or legacy
    portal_files = [
        "control_plane/app/static/portal/index.html",
        "control_plane/app/static/portal/index.legacy.html"
    ]
    portal_content = ""
    for f in portal_files:
        if (REPO_ROOT / f).exists():
            portal_content += (REPO_ROOT / f).read_text(encoding="utf-8").lower()
    
    for label in required_labels:
        if label.lower() not in portal_content:
            errors.append(f"portal dashboards missing label '{label}' (checked hub and legacy)")
        
    return errors


def validate_forbidden_patterns() -> list[str]:
    errors = []
    for relative in SCAN_PATHS:
        for path in _iter_files(relative):
            text = path.read_text(encoding="utf-8")
            lowered = text.lower()
            for token in PROHIBITED_TOKENS:
                if token in text:
                    errors.append(f"prohibited token '{token}' found in {path.relative_to(REPO_ROOT)}")
            for token in SOFT_PROHIBITED_MARKERS:
                if token in lowered:
                    errors.append(f"unexpected runtime/network marker '{token}' found in {path.relative_to(REPO_ROOT)}")
    return errors


def main() -> int:
    errors = [
        *validate_presence(),
        *validate_api_registration(),
        *validate_dashboards(),
        *validate_forbidden_patterns(),
    ]
    if errors:
        print(json.dumps({"status": "failed", "errors": errors}, indent=2))
        return 1
    print(json.dumps({"status": "passed", "phase": 82}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
