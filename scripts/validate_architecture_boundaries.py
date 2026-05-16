#!/usr/bin/env python3
"""Validate minimum architecture boundaries for the stabilization cycle."""

from __future__ import annotations

import argparse
import ast
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent
SERVICES_ROOT = REPO_ROOT / "control_plane" / "app" / "services"

SHARED_PREFIXES = (
    "app.core",
    "app.db",
    "app.models",
    "app.schemas",
    "app.utils",
)


@dataclass(frozen=True)
class DomainBoundary:
    name: str
    module_prefixes: tuple[str, ...]
    forbidden_domains: tuple[str, ...]


DOMAIN_BOUNDARIES: dict[str, DomainBoundary] = {
    "runtime": DomainBoundary(
        name="Runtime Fabric",
        module_prefixes=(
            "app.services.runtime",
            "app.services.routing",
            "app.services.providers",
            "app.services.cache",
            "app.services.workflows",
            "app.services.backend_registry",
            "app.services.backend_slot_manager",
            "app.services.queue_manager",
            "app.services.circuit_breaker",
            "app.services.inference_proxy",
            "app.services.generation_jobs",
            "app.services.embeddings",
            "app.services.embeddings_mock",
            "app.services.context_manager",
        ),
        forbidden_domains=(),
    ),
    "governance": DomainBoundary(
        name="Governance Plane",
        module_prefixes=(
            "app.services.governance",
            "app.services.model_policy",
            "app.services.commercial_guardrails",
            "app.services.compliance.operational_controls",
        ),
        forbidden_domains=(),
    ),
    "trust": DomainBoundary(
        name="Trust Plane",
        module_prefixes=(
            "app.services.security",
            "app.services.agents",
            "app.services.inference.confidential_runtime",
            "app.services.inference.cryptographic_receipts",
            "app.services.inference.execution_proofs",
            "app.services.inference.merkle_timelines",
            "app.services.inference.public_attestation_gateway",
            "app.services.inference.receipt_verification",
            "app.services.inference.replay_verification",
            "app.services.inference.transparency_gossip",
            "app.services.inference.witness_federation",
            "app.services.models.runtime_attestation",
            "app.services.models.runtime_integrity_monitor",
            "app.services.models.signed_model_registry",
        ),
        forbidden_domains=("governance", "operations", "sovereign"),
    ),
    "financial": DomainBoundary(
        name="Financial Plane",
        module_prefixes=(
            "app.services.billing",
            "app.services.payment_adapters",
            "app.services.payment_topups",
            "app.services.billing_scheduler",
            "app.services.notifications.revenue_alerts",
            "app.services.notifications.revenue_escalations",
            "app.services.compliance.financial_controls",
        ),
        forbidden_domains=("governance", "operations", "sovereign"),
    ),
    "sovereign": DomainBoundary(
        name="Sovereign Plane",
        module_prefixes=(
            "app.services.mesh",
            "app.services.inference.sovereign_appliance",
            "app.services.governance.airgap_sync",
        ),
        forbidden_domains=("financial", "operations"),
    ),
    "operations": DomainBoundary(
        name="Operations Plane",
        module_prefixes=(
            "app.services.audit",
            "app.services.admin_model_management",
            "app.services.export_reporting",
            "app.services.public_onboarding",
            "app.services.seed",
            "app.services.security_monitor",
            "app.services.compliance.customer_audit_portal",
            "app.services.compliance.portal_rbac",
        ),
        forbidden_domains=("governance", "sovereign"),
    ),
}


def iter_service_files() -> Iterable[Path]:
    yield from sorted(path for path in SERVICES_ROOT.rglob("*.py") if "__pycache__" not in path.parts)


def module_name_for(path: Path) -> str:
    relative = path.relative_to(SERVICES_ROOT).with_suffix("")
    return "app.services." + ".".join(relative.parts)


def classify_domain(module_name: str) -> str | None:
    for key, boundary in DOMAIN_BOUNDARIES.items():
        for prefix in boundary.module_prefixes:
            if module_name == prefix or module_name.startswith(prefix + "."):
                return key
    return None


def _resolve_import_from(module_name: str, node: ast.ImportFrom) -> str | None:
    if node.level == 0:
        return node.module

    package_parts = module_name.split(".")[:-1]
    keep = len(package_parts) - (node.level - 1)
    if keep <= 0:
        return node.module
    base_parts = package_parts[:keep]
    if node.module:
        return ".".join(base_parts + node.module.split("."))
    return ".".join(base_parts)


def imported_modules_for(path: Path) -> set[str]:
    module_name = module_name_for(path)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            resolved = _resolve_import_from(module_name, node)
            if resolved:
                imported.add(resolved)
    return imported


def find_boundary_violations() -> list[dict[str, str]]:
    violations: list[dict[str, str]] = []
    for path in iter_service_files():
        source_module = module_name_for(path)
        source_domain = classify_domain(source_module)
        if not source_domain:
            continue
        forbidden = set(DOMAIN_BOUNDARIES[source_domain].forbidden_domains)
        if not forbidden:
            continue
        for imported_module in sorted(imported_modules_for(path)):
            if imported_module.startswith(SHARED_PREFIXES):
                continue
            target_domain = classify_domain(imported_module)
            if not target_domain or target_domain not in forbidden:
                continue
            violations.append(
                {
                    "source_domain": DOMAIN_BOUNDARIES[source_domain].name,
                    "target_domain": DOMAIN_BOUNDARIES[target_domain].name,
                    "source_module": source_module,
                    "target_module": imported_module,
                    "path": str(path.relative_to(REPO_ROOT)),
                }
            )
    return violations


def _format_text(violations: list[dict[str, str]]) -> str:
    if not violations:
        return "Architecture boundary validation passed."
    lines = ["Architecture boundary violations detected:"]
    for violation in violations:
        lines.append(
            "- {path}: {source_module} ({source_domain}) imports {target_module} ({target_domain})".format(
                **violation
            )
        )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit violations as JSON.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    violations = find_boundary_violations()
    if args.json:
        print(json.dumps(violations, indent=2, sort_keys=True))
    else:
        print(_format_text(violations))
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
