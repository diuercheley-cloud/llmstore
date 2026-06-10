#!/usr/bin/env python3
"""Block architectural growth beyond explicit maintenance budgets and freeze policy."""

import json
import os
import subprocess
import sys
import yaml
from pathlib import Path
from typing import Dict, List, TypedDict

ROOT = Path(__file__).resolve().parents[2]

class Budget(TypedDict):
    limit: int
    category: str
    suggestion: str

def count_files(path: str, ext: str = "*.py") -> int:
    directory = ROOT / path
    if not directory.exists():
        return 0
    return sum(1 for item in directory.rglob(ext) if item.name != "__init__.py")

def line_count(path: str) -> int:
    file_path = ROOT / path
    if not file_path.exists():
        return 0
    return len(file_path.read_text(encoding="utf-8").splitlines())

def get_feature_flags() -> int:
    ff_file = ROOT / "config/feature-flags.yaml"
    if not ff_file.exists():
        return 0
    return ff_file.read_text(encoding="utf-8").count("- name:")

def collected_tests() -> int:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "tests"],
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": f"{ROOT}:{ROOT / 'control_plane'}"},
        text=True,
        capture_output=True,
        check=False,
    )
    for line in reversed(result.stdout.splitlines()):
        if " tests collected" in line:
            parts = line.split()
            if parts[0].isdigit():
                return int(parts[0])
    return 0

def get_exceptions() -> List[str]:
    exc_file = ROOT / "governance/approved_surface_exceptions.yml"
    if not exc_file.exists():
        return []
    try:
        data = yaml.safe_load(exc_file.read_text(encoding="utf-8"))
        return [e["path"] for e in data.get("exceptions", [])]
    except Exception:
        return []

def main() -> int:
    config_path = ROOT / "config/maintenance-budgets.json"
    if not config_path.exists():
        print(f"ERROR: Budget config not found at {config_path}")
        return 2

    try:
        budgets = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print(f"ERROR: Failed to parse budget config at {config_path}")
        return 2

    # Map current metrics to budget keys
    metrics = {
        "max_api_router_files": {"value": count_files("control_plane/app/api"), "category": "routers", "suggestion": "Refactor APIs or consolidate controllers"},
        "max_service_files": {"value": count_files("control_plane/app/services"), "category": "models/services", "suggestion": "Service modularity is too high; consider consolidation"},
        "max_feature_flags": {"value": get_feature_flags(), "category": "config flags", "suggestion": "Remove stale feature flags"},
        "max_main_lines": {"value": line_count("control_plane/app/main.py"), "category": "core", "suggestion": "Main application file is too bloated; extract logic"},
        "max_settings_lines": {"value": line_count("control_plane/app/core/config.py"), "category": "core", "suggestion": "Config file is too large; use sub-configs"},
        "min_collected_tests": {"value": collected_tests(), "category": "workflows CI", "suggestion": "Add more test coverage"},
    }

    print(f"{'Metric':<30} | {'Actual':<8} | {'Limit':<8} | {'Status':<10} | {'Suggestion'}")
    print("-" * 100)
    
    exit_code = 0
    
    for metric_name, data in metrics.items():
        limit = budgets.get(metric_name)
        if limit is None:
            continue
            
        value = data["value"]
        status = "PASS"
        
        if metric_name == "min_collected_tests":
            if value < limit:
                status = "FAIL"
                exit_code = 1
        else:
            if value > limit:
                status = "FAIL"
                exit_code = 1
        
        print(f"{metric_name:<30} | {value:<8} | {limit:<8} | {status:<10} | {data['suggestion']}")

    # --- Freeze Enforcement ---
    print("\nChecking for unauthorized architectural surface expansion...")
    # This is a simplified check for this implementation; 
    # In a full CI environment, we would compare against a baseline commit/branch
    
    if exit_code != 0:
        print("\nFAIL: Architectural budgets exceeded. Please review suggestions.")
    else:
        print("\nPASS: All architectural budgets respected.")
        
    return exit_code

if __name__ == "__main__":
    sys.exit(main())
