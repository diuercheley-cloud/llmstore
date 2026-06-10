#!/usr/bin/env python3
"""Validate Phase 69 Predictive Failure Signals + Deterministic Forecasting readiness."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

REQUIRED_PATHS: dict[str, Path] = {
    "Phase 69 Doc": REPO_ROOT
    / "docs"
    / "phases"
    / "phase_69_predictive_failure_signals.md",
    "Failure Signals Model": REPO_ROOT
    / "control_plane"
    / "app"
    / "models"
    / "operations"
    / "failure_signals.py",
    "Deterministic Engine": REPO_ROOT
    / "control_plane"
    / "app"
    / "services"
    / "operations"
    / "forecasting"
    / "deterministic_engine.py",
    "Risk Scoring Service": REPO_ROOT
    / "control_plane"
    / "app"
    / "services"
    / "operations"
    / "forecasting"
    / "risk_scoring.py",
    "Receipts Service": REPO_ROOT
    / "control_plane"
    / "app"
    / "services"
    / "operations"
    / "forecasting"
    / "receipts.py",
    "Audit Events Service": REPO_ROOT
    / "control_plane"
    / "app"
    / "services"
    / "operations"
    / "forecasting"
    / "audit_events.py",
    "Operations Admin API": REPO_ROOT
    / "control_plane"
    / "app"
    / "api"
    / "operations_admin.py",
    "Alembic Migration": REPO_ROOT
    / "control_plane"
    / "alembic"
    / "versions"
    / "phase69_failure_signals.py",
    "Model Tests": REPO_ROOT
    / "tests"
    / "operations"
    / "test_failure_signal_models.py",
    "Engine Tests": REPO_ROOT
    / "tests"
    / "operations"
    / "test_deterministic_forecasting_engine.py",
    "Risk Scoring Tests": REPO_ROOT
    / "tests"
    / "operations"
    / "test_failure_risk_scoring.py",
    "Receipts Tests": REPO_ROOT
    / "tests"
    / "operations"
    / "test_failure_forecasting_receipts.py",
    "Audit Events Tests": REPO_ROOT
    / "tests"
    / "operations"
    / "test_failure_forecasting_audit_events.py",
    "API Tests": REPO_ROOT
    / "tests"
    / "operations"
    / "test_failure_forecasting_api.py",
}

REQUIRED_MAKE_TARGETS = (
    "validate-phase-69-failure-forecasting",
)

# Targeted list — do NOT run tests/integration/operations/ broadly to avoid
# excessive execution in the validate-architecture aggregate.
PHASE_69_TEST_FILES = [
    "tests/integration/operations/test_failure_signal_models.py",
    "tests/integration/operations/test_deterministic_forecasting_engine.py",
    "tests/integration/operations/test_failure_risk_scoring.py",
    "tests/integration/operations/test_failure_forecasting_receipts.py",
    "tests/integration/operations/test_failure_forecasting_audit_events.py",
    "tests/integration/operations/test_failure_forecasting_api.py",
]


def validate_required_paths() -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    for name, path in REQUIRED_PATHS.items():
        if not path.exists():
            failures.append(
                {
                    "path": str(path.relative_to(REPO_ROOT)),
                    "issue": f"missing required artifact: {name}",
                }
            )
    return failures


def validate_makefile_targets() -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    makefile = REPO_ROOT / "Makefile"
    if not makefile.exists():
        return [{"path": "Makefile", "issue": "missing file"}]
    content = makefile.read_text(encoding="utf-8")
    for target in REQUIRED_MAKE_TARGETS:
        if f"{target}:" not in content:
            failures.append(
                {"path": "Makefile", "issue": f"missing target: {target}"}
            )
    return failures


def _python() -> str:
    """Return the venv python if available, else system python3."""
    venv_py = REPO_ROOT / ".venv" / "bin" / "python"
    return str(venv_py) if venv_py.exists() else "python3"


def validate_tests_pass() -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    python = _python()
    result = subprocess.run(
        [python, "-m", "pytest", *PHASE_69_TEST_FILES, "-x", "--tb=short", "-q"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        failures.append(
            {
                "path": "Phase 69 targeted tests",
                "issue": (
                    f"Phase 69 tests failed ({result.returncode}): "
                    f"{result.stdout.strip() or result.stderr.strip() or 'no output'}"
                ),
            }
        )
    return failures


def validate_all(smoke: bool = False) -> list[dict[str, str]]:
    failures = [
        *validate_required_paths(),
        *validate_makefile_targets(),
    ]
    if not smoke:
        failures.extend(validate_tests_pass())
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit failures as JSON.")
    parser.add_argument("--smoke", action="store_true", help="Skip slow pytest suite.")
    args = parser.parse_args()

    failures = validate_all(smoke=args.smoke)
    if args.json:
        print(json.dumps(failures, indent=2, sort_keys=True))
    elif failures:
        print("Phase 69 failure forecasting validation failed:")
        for failure in failures:
            print(f"- {failure['path']}: {failure['issue']}")
    else:
        print("Phase 69 failure forecasting validation passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
