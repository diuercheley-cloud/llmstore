#!/usr/bin/env python3
"""Block architectural growth beyond explicit maintenance budgets."""

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def count_files(path: str) -> int:
    return sum(1 for item in (ROOT / path).rglob("*.py") if item.name != "__init__.py")


def line_count(path: str) -> int:
    return len((ROOT / path).read_text(encoding="utf-8").splitlines())


def collected_tests() -> int:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "tests", "control_plane/tests"],
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": f"{ROOT}:{ROOT / 'control_plane'}"},
        text=True,
        capture_output=True,
        check=False,
    )
    for line in reversed(result.stdout.splitlines()):
        if " tests collected" in line:
            return int(line.split()[0])
    return 0


def main() -> int:
    budgets = json.loads((ROOT / "config/maintenance-budgets.json").read_text(encoding="utf-8"))
    flags = (ROOT / "config/feature-flags.yaml").read_text(encoding="utf-8").count("- name:")
    metrics = {
        "max_api_router_files": count_files("control_plane/app/api"),
        "max_service_files": count_files("control_plane/app/services"),
        "max_feature_flags": flags,
        "max_main_lines": line_count("control_plane/app/main.py"),
        "max_settings_lines": line_count("control_plane/app/core/config.py"),
    }
    failures = [
        f"{name}: {value} > {budgets[name]}"
        for name, value in metrics.items()
        if value > budgets[name]
    ]
    tests = collected_tests()
    if tests < budgets["min_collected_tests"]:
        failures.append(f"collected tests: {tests} < {budgets['min_collected_tests']}")
    if failures:
        print("FAIL: Maintenance budgets exceeded:")
        print("\n".join(f" - {failure}" for failure in failures))
        return 1
    print(f"PASS: Maintenance budgets respected: {metrics}, collected_tests={tests}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
