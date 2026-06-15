#!/usr/bin/env python3
"""Run the platform architecture validation suite using local validation scripts only."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass(frozen=True)
class ValidationTarget:
    """Represents one local validation script in the architecture suite."""

    name: str
    script_path: Path


VALIDATION_TARGETS = (
    ValidationTarget(
        "Architecture Boundaries", REPO_ROOT / "scripts" / "validate_architecture_boundaries.py"
    ),
    ValidationTarget("Runtime Contracts", REPO_ROOT / "scripts" / "validate_runtime_contracts.py"),
    ValidationTarget("Domain Contracts", REPO_ROOT / "scripts" / "validate_domain_contracts.py"),
    ValidationTarget("ADRs", REPO_ROOT / "scripts" / "validate_adrs.py"),
    ValidationTarget("Invariants", REPO_ROOT / "scripts" / "validate_invariants.py"),
)


def run_target(target: ValidationTarget) -> tuple[str, int, str]:
    """Run one validation target and return status, exit code, and summarized output."""

    if not target.script_path.exists():
        return ("SKIP", 0, f"{target.script_path.relative_to(REPO_ROOT)} not available")

    result = subprocess.run(
        [sys.executable, str(target.script_path)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    output = (result.stdout or result.stderr).strip()
    status = "PASS" if result.returncode == 0 else "FAIL"
    return (status, result.returncode, output or "no output")


def main() -> int:
    print("Platform architecture validation suite")
    print(f"Repository: {REPO_ROOT}")
    print("Mode: offline-only local validators")
    print("")

    had_failure = False
    for target in VALIDATION_TARGETS:
        status, exit_code, output = run_target(target)
        print(f"[{status}] {target.name} -> {target.script_path.relative_to(REPO_ROOT)}")
        print(f"exit_code={exit_code}")
        print(output)
        print("")
        if status == "FAIL":
            had_failure = True

    if had_failure:
        print("Platform architecture validation failed.")
        return 1

    print("Platform architecture validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
