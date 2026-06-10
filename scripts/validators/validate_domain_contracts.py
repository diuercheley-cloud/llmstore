#!/usr/bin/env python3
"""Validate lightweight domain contract structure for future modularization."""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DOMAINS_ROOT = REPO_ROOT / "control_plane" / "app" / "domains"
DOC_PATH = REPO_ROOT / "docs" / "architecture" / "domain_contracts.md"

CONTROL_PLANE_ROOT = REPO_ROOT / "control_plane"
if str(CONTROL_PLANE_ROOT) not in sys.path:
    sys.path.insert(0, str(CONTROL_PLANE_ROOT))

REQUIRED_FIELDS = (
    "allowed_inputs",
    "emitted_events",
    "forbidden_dependencies",
    "deterministic_requirements",
)

DOMAIN_SPECS = {
    "runtime": "RuntimeDomainContract",
    "governance": "GovernanceDomainContract",
    "trust": "TrustDomainContract",
    "financial": "FinancialDomainContract",
    "sovereign": "SovereignDomainContract",
    "operations": "OperationsDomainContract",
}

REQUIRED_DOC_FRAGMENTS = (
    "# Domain Contracts",
    "offline-first",
    "allowed_inputs",
    "emitted_events",
    "forbidden_dependencies",
    "deterministic_requirements",
    "Runtime",
    "Governance",
    "Trust",
    "Financial",
    "Sovereign",
    "Operations",
)


def validate_domain_files() -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    for domain in DOMAIN_SPECS:
        domain_root = DOMAINS_ROOT / domain
        for filename in ("__init__.py", "README.md", "contracts.py", "events.py", "exceptions.py"):
            path = domain_root / filename
            if not path.exists():
                failures.append({"path": str(path.relative_to(REPO_ROOT)), "issue": "missing file"})
    return failures


def validate_contract_classes() -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    for domain, class_name in DOMAIN_SPECS.items():
        module = importlib.import_module(f"app.domains.{domain}.contracts")
        contract = getattr(module, class_name, None)
        if contract is None:
            failures.append({"path": f"app.domains.{domain}.contracts", "issue": f"missing class {class_name}"})
            continue
        for field_name in REQUIRED_FIELDS:
            value = getattr(contract, field_name, None)
            if not value:
                failures.append(
                    {"path": f"app.domains.{domain}.contracts.{class_name}", "issue": f"missing field {field_name}"}
                )
                continue
            if not isinstance(value, tuple):
                failures.append(
                    {
                        "path": f"app.domains.{domain}.contracts.{class_name}",
                        "issue": f"field {field_name} must be a tuple",
                    }
                )
        forbidden = getattr(contract, "forbidden_dependencies", ())
        if any(dep.startswith("app.domains.") and dep.endswith(f".{domain}") for dep in forbidden):
            failures.append(
                {
                    "path": f"app.domains.{domain}.contracts.{class_name}",
                    "issue": "forbidden_dependencies must not reference the same domain",
                }
            )
    return failures


def validate_documentation() -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    if not DOC_PATH.exists():
        return [{"path": str(DOC_PATH.relative_to(REPO_ROOT)), "issue": "missing file"}]
    content = DOC_PATH.read_text(encoding="utf-8")
    for fragment in REQUIRED_DOC_FRAGMENTS:
        if fragment not in content:
            failures.append({"path": str(DOC_PATH.relative_to(REPO_ROOT)), "issue": f"missing fragment: {fragment}"})
    return failures


def validate_all() -> list[dict[str, str]]:
    return [
        *validate_domain_files(),
        *validate_contract_classes(),
        *validate_documentation(),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit failures as JSON.")
    args = parser.parse_args()

    failures = validate_all()
    if args.json:
        print(json.dumps(failures, indent=2, sort_keys=True))
    elif failures:
        print("Domain contract validation failed:")
        for failure in failures:
            print(f"- {failure['path']}: {failure['issue']}")
    else:
        print("Domain contract validation passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
