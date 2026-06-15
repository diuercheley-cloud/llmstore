#!/usr/bin/env python3
"""Validate the Governance Documentation Foundation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RFC_ROOT = REPO_ROOT / "docs" / "rfc"
GOVERNANCE_ROOT = REPO_ROOT / "docs" / "governance"
SECURITY_ROOT = REPO_ROOT / "docs" / "security"

REQUIRED_RFC_FILES = (
    "README.md",
    "0000-rfc-process.md",
    "0001-extension-runtime-governance.md",
    "0002-sovereign-federation-governance.md",
)

REQUIRED_GOVERNANCE_FILES = (
    "architecture_decision_governance.md",
    "semantic_version_governance_policy.md",
    "extension_compatibility_policy.md",
    "plugin_certification_workflow_placeholder.md",
    "threat_modeling_framework.md",
    "supply_chain_governance.md",
    "governance_documentation_foundation_summary.md",
)

REQUIRED_SECURITY_FILES = (
    "threat_model_template.md",
    "supply_chain_risk_register.md",
)

REQUIRED_RFC_SECTIONS = (
    "## Summary",
    "## Context",
    "## Goals",
    "## Non-Goals",
    "## Design",
    "## Security Considerations",
    "## Determinism Impact",
    "## Offline Compatibility",
    "## Tenant Isolation Impact",
    "## Rollback Plan",
)

REQUIRED_GOVERNANCE_MARKERS = (
    "offline compatibility",
    "determinism",
    "tenant isolation",
)

PLUGIN_CERTIFICATION_MARKERS = (
    "placeholder-only",
    "not a real certification",
)

SUPPLY_CHAIN_MARKERS = (
    "no mandatory saas or cloud",
    "no mandatory saas or cloud service",
    "no mandatory saas or cloud control plane",
)

STRIDE_MARKERS = (
    "spoofing",
    "tampering",
    "repudiation",
    "information disclosure",
    "denial of service",
    "elevation of privilege",
)

PROHIBITED_CLAIMS = (
    "military-grade",
    "formally certified",
    "guaranteed secure",
    "government certified",
    "real hardware attestation",
    "certified confidential computing",
    "certified plugin",
)


def _rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def _iter_governance_docs() -> list[Path]:
    return [GOVERNANCE_ROOT / name for name in REQUIRED_GOVERNANCE_FILES]


def _iter_rfc_docs() -> list[Path]:
    return [RFC_ROOT / name for name in REQUIRED_RFC_FILES if name != "README.md"]


def validate_required_paths() -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    if not RFC_ROOT.exists():
        failures.append({"path": _rel(RFC_ROOT), "issue": "missing directory"})
    if not GOVERNANCE_ROOT.exists():
        failures.append({"path": _rel(GOVERNANCE_ROOT), "issue": "missing directory"})
    for filename in REQUIRED_RFC_FILES:
        path = RFC_ROOT / filename
        if not path.exists():
            failures.append({"path": _rel(path), "issue": "missing file"})
    for filename in REQUIRED_GOVERNANCE_FILES:
        path = GOVERNANCE_ROOT / filename
        if not path.exists():
            failures.append({"path": _rel(path), "issue": "missing file"})
    for filename in REQUIRED_SECURITY_FILES:
        path = SECURITY_ROOT / filename
        if not path.exists():
            failures.append({"path": _rel(path), "issue": "missing file"})
    return failures


def validate_rfc_sections() -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    for path in _iter_rfc_docs():
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        for section in REQUIRED_RFC_SECTIONS:
            if section not in content:
                failures.append({"path": _rel(path), "issue": f"missing RFC section: {section}"})
    return failures


def validate_governance_markers() -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    for path in _iter_governance_docs():
        if not path.exists():
            continue
        lowered = path.read_text(encoding="utf-8").lower()
        for marker in REQUIRED_GOVERNANCE_MARKERS:
            if marker not in lowered:
                failures.append(
                    {"path": _rel(path), "issue": f"missing governance marker: {marker}"}
                )
    return failures


def validate_plugin_certification_doc() -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    path = GOVERNANCE_ROOT / "plugin_certification_workflow_placeholder.md"
    if not path.exists():
        return failures
    lowered = path.read_text(encoding="utf-8").lower()
    for marker in PLUGIN_CERTIFICATION_MARKERS:
        if marker not in lowered:
            failures.append(
                {"path": _rel(path), "issue": f"missing plugin certification marker: {marker}"}
            )
    return failures


def validate_supply_chain_doc() -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    path = GOVERNANCE_ROOT / "supply_chain_governance.md"
    if not path.exists():
        return failures
    lowered = path.read_text(encoding="utf-8").lower()
    if not any(marker in lowered for marker in SUPPLY_CHAIN_MARKERS):
        failures.append(
            {"path": _rel(path), "issue": "missing prohibition on mandatory SaaS/cloud"}
        )
    return failures


def validate_threat_model_doc() -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    path = GOVERNANCE_ROOT / "threat_modeling_framework.md"
    if not path.exists():
        return failures
    lowered = path.read_text(encoding="utf-8").lower()
    for marker in STRIDE_MARKERS:
        if marker not in lowered:
            failures.append(
                {"path": _rel(path), "issue": f"missing STRIDE-like category: {marker}"}
            )
    return failures


def validate_prohibited_claims() -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    doc_roots = (RFC_ROOT, GOVERNANCE_ROOT, SECURITY_ROOT)
    for root in doc_roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.md")):
            lowered = path.read_text(encoding="utf-8").lower()
            for claim in PROHIBITED_CLAIMS:
                if claim in lowered:
                    failures.append(
                        {"path": _rel(path), "issue": f"contains prohibited claim: {claim}"}
                    )
    return failures


def validate() -> list[dict[str, str]]:
    return [
        *validate_required_paths(),
        *validate_rfc_sections(),
        *validate_governance_markers(),
        *validate_plugin_certification_doc(),
        *validate_supply_chain_doc(),
        *validate_threat_model_doc(),
        *validate_prohibited_claims(),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit failures as JSON.")
    args = parser.parse_args()

    failures = validate()
    if args.json:
        print(json.dumps(failures, indent=2, sort_keys=True))
    elif failures:
        print("Governance documentation foundation validation failed:")
        for failure in failures:
            print(f"- {failure['path']}: {failure['issue']}")
    else:
        print("Governance documentation foundation validation passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
