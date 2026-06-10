#!/usr/bin/env python3
"""Validate architectural readiness prerequisites before Phase 66 implementation."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

REQUIRED_PATHS = {
    "Core Runtime Spec": REPO_ROOT / "docs" / "runtime" / "core_runtime_spec.md",
    "Domain Boundaries": REPO_ROOT / "docs" / "architecture" / "domain_boundaries.md",
    "ADRs": REPO_ROOT / "docs" / "adr" / "README.md",
    "Invariants Documentation": REPO_ROOT / "docs" / "architecture" / "invariants.md",
    "Architecture Validation Suite": REPO_ROOT / "scripts" / "validate_platform_architecture.py",
    "Claims Policy": REPO_ROOT / "docs" / "compliance" / "claims_policy.md",
    "Phase 66 Readiness Gate": REPO_ROOT / "docs" / "phases" / "phase_66_readiness_gate.md",
}

REQUIRED_MAKE_TARGETS = (
    "validate-runtime-contracts",
    "validate-domain-contracts",
    "validate-invariants",
    "validate-adrs",
    "validate-claims",
    "validate-platform-architecture",
    "validate-phase-66-readiness",
)

OFFLINE_VALIDATION_SCRIPTS = (
    "validate_runtime_contracts.py",
    "validate_domain_contracts.py",
    "validate_invariants.py",
    "validate_adrs.py",
    "validate_claims.py",
    "validate_platform_architecture.py",
)


def validate_required_paths() -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    for name, path in REQUIRED_PATHS.items():
        if not path.exists():
            failures.append({"path": str(path.relative_to(REPO_ROOT)), "issue": f"missing required artifact: {name}"})
    return failures


def validate_makefile_targets() -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    makefile = REPO_ROOT / "Makefile"
    if not makefile.exists():
        return [{"path": "Makefile", "issue": "missing file"}]
    content = makefile.read_text(encoding="utf-8")
    for target in REQUIRED_MAKE_TARGETS:
        if f"{target}:" not in content:
            failures.append({"path": "Makefile", "issue": f"missing target: {target}"})
    return failures


def run_local_validator(script_name: str) -> dict[str, str] | None:
    script_path = REPO_ROOT / "scripts" / script_name
    if not script_path.exists():
        return {"path": str(script_path.relative_to(REPO_ROOT)), "issue": "missing offline validation script"}

    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        output = (result.stdout or result.stderr).strip()
        return {
            "path": str(script_path.relative_to(REPO_ROOT)),
            "issue": f"offline validation script failed: {output or 'no output'}",
        }
    return None


def validate_offline_scripts() -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    for script_name in OFFLINE_VALIDATION_SCRIPTS:
        failure = run_local_validator(script_name)
        if failure:
            failures.append(failure)
    return failures


def validate_all() -> list[dict[str, str]]:
    return [
        *validate_required_paths(),
        *validate_makefile_targets(),
        *validate_offline_scripts(),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit failures as JSON.")
    args = parser.parse_args()

    failures = validate_all()
    if args.json:
        print(json.dumps(failures, indent=2, sort_keys=True))
    elif failures:
        print("Phase 66 readiness validation failed:")
        for failure in failures:
            print(f"- {failure['path']}: {failure['issue']}")
    else:
        print("Phase 66 readiness validation passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

