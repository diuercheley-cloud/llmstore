#!/usr/bin/env python3
"""Measure duration and exit code of Makefile validation targets."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

DEFAULT_TARGETS = [
    "validate-makefile-governance",
    "validate-governance-documentation-foundation",
    "validate-phase-69-failure-forecasting",
    "validate-phase-70-correlation-engine",
    "validate-phase-71-remediation-planning",
    "validate-phase-72-remediation-execution",
    "validate-phase-73-adapter-sandbox",
    "validate-phase-74-adapter-registry",
    "validate-phase-75-adapter-promotion",
    "validate-phase-76-attestation-framework",
    "validate-phase-77-federation-sync",
    "validate-phase-78-compatibility-contracts",
    "validate-phase-79-plugin-runtime",
    "validate-phase-80-plugin-supply-chain",
    "validate-phase-81-reproducible-builds",
    "validate-phase-82-platform-sustainability",
]


def run_target(target: str, timeout: int | None = None) -> dict:
    start = time.monotonic()
    try:
        result = subprocess.run(
            ["make", "--no-print-directory", target],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        exit_code = result.returncode
        status = "PASS" if exit_code == 0 else "FAIL"
    except subprocess.TimeoutExpired:
        exit_code = -1
        status = "TIMEOUT"
        result = None

    elapsed = time.monotonic() - start

    return {
        "target": target,
        "status": status,
        "exit_code": exit_code,
        "elapsed_seconds": round(elapsed, 2),
        "output_summary": ((result.stdout.strip() or "")[-200:] if result else ""),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--targets",
        nargs="*",
        default=DEFAULT_TARGETS,
        help="Targets to measure (default: all phase targets)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="Per-target timeout in seconds (default 600)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON report to stdout",
    )
    parser.add_argument(
        "--report-dir",
        type=str,
        default=str(REPO_ROOT / "docs" / "validation"),
        help="Output directory for reports (default: docs/validation)",
    )
    args = parser.parse_args()

    results = []
    for target in args.targets:
        print(f"Measuring {target} ...", file=sys.stderr)
        result = run_target(target, timeout=args.timeout)
        results.append(result)
        print(
            f"  {result['status']} ({result['elapsed_seconds']:.1f}s)",
            file=sys.stderr,
        )

    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)

    json_path = report_dir / "validation_target_timings.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Wrote {json_path}", file=sys.stderr)

    md_path = report_dir / "validation_target_timings.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Validation Target Timings\n\n")
        f.write("| Target | Status | Time (s) |\n")
        f.write("|---|---|---|\n")
        for r in results:
            f.write(f"| {r['target']} | {r['status']} | {r['elapsed_seconds']} |\n")

        total = sum(r["elapsed_seconds"] for r in results)
        passed = sum(1 for r in results if r["status"] == "PASS")
        failed = sum(1 for r in results if r["status"] == "FAIL")
        timedout = sum(1 for r in results if r["status"] == "TIMEOUT")

        f.write(f"\n**Total elapsed: {total:.1f}s**\n")
        f.write(f"\n**Passed: {passed} | Failed: {failed} | Timed out: {timedout}**\n")
    print(f"Wrote {md_path}", file=sys.stderr)

    if args.json:
        print(json.dumps(results, indent=2))

    failed_results = [r for r in results if r["status"] != "PASS"]
    return len(failed_results)


if __name__ == "__main__":
    raise SystemExit(main())
