#!/usr/bin/env python3
"""Validate Architectural Decision Records structure and prohibited claims."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ADR_ROOT = REPO_ROOT / "docs" / "adr"

REQUIRED_FILES = (
    "README.md",
    "0001-deterministic-runtime.md",
    "0002-offline-first-sovereign-mode.md",
    "0003-cryptographic-receipts.md",
    "0004-governance-policy-gates.md",
    "0005-no-mandatory-saas.md",
    "0006-placeholder-attestation-policy.md",
    "0007-route-surface-governance.md",
    "0008-generated-documentation-rebuildable-artifacts.md",
    "0009-backup-restore-component-architecture.md",
    "0010-domain-persistence-contracts.md",
    "0011-disaster-recovery-test-matrix.md",
)

LEGACY_REQUIRED_SECTIONS = (
    "## Status",
    "## Context",
    "## Decision",
    "## Consequences",
    "## Security Notes",
    "## Offline Compatibility",
    "## Determinism Impact",
)

CURRENT_REQUIRED_SECTIONS = (
    "## Status",
    "## Data",
    "## Contexto",
    "## Decisao",
    "## Alternativas Consideradas",
    "## Consequencias",
    "## Validacoes Obrigatorias",
)

LEGACY_ADR_FILES = (
    "0001-deterministic-runtime.md",
    "0002-offline-first-sovereign-mode.md",
    "0003-cryptographic-receipts.md",
    "0004-governance-policy-gates.md",
    "0005-no-mandatory-saas.md",
    "0006-placeholder-attestation-policy.md",
)

CURRENT_ADR_FILES = (
    "0007-route-surface-governance.md",
    "0008-generated-documentation-rebuildable-artifacts.md",
    "0009-backup-restore-component-architecture.md",
    "0010-domain-persistence-contracts.md",
    "0011-disaster-recovery-test-matrix.md",
)

ALLOWED_ADR_OWNERS = (
    "platform-ops",
    "security-team",
    "security-ops",
    "core-team",
    "runtime-ops",
    "agent-platform",
    "billing-team",
    "billing-ops",
    "infra-team",
    "cloud-team",
    "model-team",
    "rag-team",
    "audio-team",
    "compliance-team",
    "qa-team",
    "graph-team",
    "product-team",
)

PROHIBITED_CLAIMS = (
    "military-grade",
    "formally certified",
    "guaranteed secure",
    "real hardware attestation",
    "government-certified PKI",
)

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def iter_adr_files() -> list[Path]:
    return [ADR_ROOT / name for name in REQUIRED_FILES if name != "README.md"]


def required_sections_for(path: Path) -> tuple[str, ...]:
    if path.name in LEGACY_ADR_FILES:
        return LEGACY_REQUIRED_SECTIONS
    return CURRENT_REQUIRED_SECTIONS


def extract_front_matter_value(content: str, key: str) -> str | None:
    if not content.startswith("---\n"):
        return None
    parts = content.split("---\n", 2)
    if len(parts) < 3:
        return None
    front_matter = parts[1]
    prefix = f"{key}:"
    for line in front_matter.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return None


def extract_section_value(content: str, heading: str) -> str | None:
    marker = f"## {heading}"
    if marker not in content:
        return None
    section = content.split(marker, 1)[1].lstrip("\n")
    lines = section.splitlines()
    for line in lines:
        if line.strip():
            return line.strip()
    return None


def validate_required_files() -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    for filename in REQUIRED_FILES:
        path = ADR_ROOT / filename
        if not path.exists():
            failures.append({"path": str(path.relative_to(REPO_ROOT)), "issue": "missing file"})
    return failures


def validate_sections() -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    for path in iter_adr_files():
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        for section in required_sections_for(path):
            if section not in content:
                failures.append(
                    {
                        "path": str(path.relative_to(REPO_ROOT)),
                        "issue": f"missing section: {section}",
                    }
                )
    return failures


def validate_prohibited_claims() -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    for path in iter_adr_files():
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8").lower()
        for claim in PROHIBITED_CLAIMS:
            if claim.lower() in content:
                failures.append(
                    {
                        "path": str(path.relative_to(REPO_ROOT)),
                        "issue": f"contains prohibited claim: {claim}",
                    }
                )
    return failures


def validate_current_adr_dates() -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    for filename in CURRENT_ADR_FILES:
        path = ADR_ROOT / filename
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        front_matter_date = extract_front_matter_value(content, "date")
        section_date = extract_section_value(content, "Data")

        if not front_matter_date:
            failures.append(
                {
                    "path": str(path.relative_to(REPO_ROOT)),
                    "issue": "missing front matter field: date",
                }
            )
        elif not DATE_PATTERN.fullmatch(front_matter_date):
            failures.append(
                {
                    "path": str(path.relative_to(REPO_ROOT)),
                    "issue": f"invalid front matter date format: {front_matter_date}",
                }
            )

        if not section_date:
            failures.append(
                {
                    "path": str(path.relative_to(REPO_ROOT)),
                    "issue": "missing value for section: Data",
                }
            )
        elif not DATE_PATTERN.fullmatch(section_date):
            failures.append(
                {
                    "path": str(path.relative_to(REPO_ROOT)),
                    "issue": f"invalid section date format: {section_date}",
                }
            )

        if front_matter_date and section_date and front_matter_date != section_date:
            failures.append(
                {
                    "path": str(path.relative_to(REPO_ROOT)),
                    "issue": f"front matter date does not match section Data: {front_matter_date} != {section_date}",
                }
            )
    return failures


def normalize_status(value: str) -> str:
    return value.strip().lower().replace("-", " ")


def validate_current_adr_status() -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    for filename in CURRENT_ADR_FILES:
        path = ADR_ROOT / filename
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        front_matter_status = extract_front_matter_value(content, "status")
        section_status = extract_section_value(content, "Status")

        if not front_matter_status:
            failures.append(
                {
                    "path": str(path.relative_to(REPO_ROOT)),
                    "issue": "missing front matter field: status",
                }
            )
            continue

        if not section_status:
            failures.append(
                {
                    "path": str(path.relative_to(REPO_ROOT)),
                    "issue": "missing value for section: Status",
                }
            )
            continue

        if normalize_status(front_matter_status) != normalize_status(section_status):
            failures.append(
                {
                    "path": str(path.relative_to(REPO_ROOT)),
                    "issue": f"front matter status does not match section Status: {front_matter_status} != {section_status}",
                }
            )
    return failures


def validate_current_adr_owner() -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    for filename in CURRENT_ADR_FILES:
        path = ADR_ROOT / filename
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        front_matter_owner = extract_front_matter_value(content, "owner")

        if not front_matter_owner:
            failures.append(
                {
                    "path": str(path.relative_to(REPO_ROOT)),
                    "issue": "missing front matter field: owner",
                }
            )
            continue

        if front_matter_owner not in ALLOWED_ADR_OWNERS:
            failures.append(
                {
                    "path": str(path.relative_to(REPO_ROOT)),
                    "issue": f"owner not allowed for ADR front matter: {front_matter_owner}",
                }
            )
    return failures


def validate_all() -> list[dict[str, str]]:
    return [
        *validate_required_files(),
        *validate_sections(),
        *validate_prohibited_claims(),
        *validate_current_adr_dates(),
        *validate_current_adr_status(),
        *validate_current_adr_owner(),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit failures as JSON.")
    args = parser.parse_args()

    failures = validate_all()
    if args.json:
        print(json.dumps(failures, indent=2, sort_keys=True))
    elif failures:
        print("ADR validation failed:")
        for failure in failures:
            print(f"- {failure['path']}: {failure['issue']}")
    else:
        print("ADR validation passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
