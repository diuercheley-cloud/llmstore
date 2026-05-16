#!/usr/bin/env python3
"""Run pytest with --durations=0 and report slow tests."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _python() -> str:
    venv_py = REPO_ROOT / ".venv" / "bin" / "python"
    return str(venv_py) if venv_py.exists() else "python3"


def get_slow_tests(
    test_dir: str,
    top_n: int = 20,
    min_duration: float = 1.0,
    timeout: int = 600,
) -> str:
    python = _python()
    cmd = [
        python,
        "-m",
        "pytest",
        test_dir,
        "--durations=0",
        "-q",
        "--tb=no",
    ]
    result = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    output = result.stdout
    stderr_output = result.stderr

    slow_lines = []
    capture = False
    for line in output.splitlines():
        if "slowest durations" in line:
            capture = True
            continue
        if capture:
            stripped = line.strip()
            if not stripped or "call" not in line:
                if "warnings" in line.lower() or not stripped:
                    continue
            if stripped and ("call" in stripped or "setup" in stripped or "teardown" in stripped):
                slow_lines.append(stripped)

    report_parts = [f"# Slow Tests Report — {test_dir}", ""]

    if not slow_lines:
        report_parts.append("No duration data captured (tests may have been skipped or none collected).")
        if result.returncode != 0:
            report_parts.append("")
            report_parts.append("## pytest output (stderr)")
            report_parts.append("```")
            report_parts.append(stderr_output.strip()[-1000:])
            report_parts.append("```")
    else:
        report_parts.append(f"Top {len(slow_lines)} slowest durations (min {min_duration}s):")
        report_parts.append("")
        report_parts.append("```")
        for line in slow_lines[:top_n]:
            report_parts.append(line)
        report_parts.append("```")

    if result.returncode != 0:
        report_parts.append("")
        report_parts.append(f"pytest exit code: {result.returncode}")

    return "\n".join(report_parts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--test-dir",
        default="tests/operations",
        help="Test directory to scan (default: tests/operations)",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=20,
        help="Number of slowest tests to report (default: 20)",
    )
    parser.add_argument(
        "--min-duration",
        type=float,
        default=1.0,
        help="Minimum duration in seconds (default: 1.0)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="pytest timeout in seconds (default: 600)",
    )
    parser.add_argument(
        "--report-dir",
        type=str,
        default=str(REPO_ROOT / "docs" / "validation"),
        help="Output directory for report (default: docs/validation)",
    )
    args = parser.parse_args()

    report = get_slow_tests(
        test_dir=args.test_dir,
        top_n=args.top_n,
        min_duration=args.min_duration,
        timeout=args.timeout,
    )

    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "slow_tests_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
        f.write("\n")
    print(report)
    print(f"\nReport written to {report_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
