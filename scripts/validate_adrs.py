#!/usr/bin/env python3
"""Validate Architectural Decision Records structure and prohibited claims."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ADR_ROOT = REPO_ROOT / "docs" / "adr"

REQUIRED_FILES = (
    "README.md",
    "0001-deterministic-runtime.md",
    "0002-offline-first-sovereign-mode.md",
    "0003-cryptographic-receipts.md",
    "0004-governance-policy-gates.md",
    "0005-no-mandatory-saas.md",
    "0006-placeholder-attestation-policy.md",
)

REQUIRED_SECTIONS = (
    "## Status",
    "## Context",
    "## Decision",
    "## Consequences",
    "## Security Notes",
    "## Offline Compatibility",
    "## Determinism Impact",
)

PROHIBITED_CLAIMS = (
    "military-grade",
    "formally certified",
    "guaranteed secure",
    "real hardware attestation",
    "government-certified PKI",
)


def iter_adr_files() -> list[Path]:
    return [ADR_ROOT / name for name in REQUIRED_FILES if name != "README.md"]


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
        for section in REQUIRED_SECTIONS:
            if section not in content:
                failures.append({"path": str(path.relative_to(REPO_ROOT)), "issue": f"missing section: {section}"})
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
                    {"path": str(path.relative_to(REPO_ROOT)), "issue": f"contains prohibited claim: {claim}"}
                )
    return failures


def validate_all() -> list[dict[str, str]]:
    return [*validate_required_files(), *validate_sections(), *validate_prohibited_claims()]


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

