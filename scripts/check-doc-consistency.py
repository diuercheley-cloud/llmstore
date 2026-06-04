#!/usr/bin/env python3
import os
import re
import sys

import yaml

SUPPORTED_SURFACE_YAML = "config/supported-surface.yaml"

def load_capabilities():
    with open(SUPPORTED_SURFACE_YAML, "r") as f:
        data = yaml.safe_load(f)
        return data.get("capabilities", [])

def check_contradictions(content, file_path):
    errors = []
    
    contradictory_pairs = [
        (r"no real plugin execution", r"sandboxed local execution"),
        (r"attestation is policy-only", r"hardware-backed trust")
    ]
    
    for p1, p2 in contradictory_pairs:
        if re.search(p1, content, re.I) and re.search(p2, content, re.I):
            errors.append(f"Contradiction found in {file_path}: '{p1}' vs '{p2}'")
            
    return errors

def main():
    if not os.path.exists(SUPPORTED_SURFACE_YAML):
        print(f"Error: {SUPPORTED_SURFACE_YAML} not found")
        return
        
    capabilities = load_capabilities()
    cap_map = {c["id"]: c for f in capabilities for c in [f] if "id" in f}
    
    print("--- Running Documentation Consistency Check ---")
    
    files_to_check = [
        "docs/architecture/platform_overview.md",
        "docs/architecture/platform_guarantees_and_limitations.md",
        "README.md",
        "SECURITY.md"
    ]
    
    overall_errors = 0
    
    for file_path in files_to_check:
        if not os.path.exists(file_path):
            print(f"[SKIP] {file_path} not found")
            continue
            
        print(f"Checking {file_path}...")
        with open(file_path, "r") as f:
            content = f.read()
            
        file_errors = check_contradictions(content, file_path)
        for err in file_errors:
            print(f" - [FAIL] {err}")
            overall_errors += 1
            
        for cap_id, cap_info in cap_map.items():
            name = cap_info["name"]
            status = cap_info["status"]
            
            if status in ["supported", "production_ready"]:
                if re.search(f"- no real {name.lower()}", content, re.I):
                     print(f" - [FAIL] {file_path} claims 'no real {name}' but capability is '{status}'")
                     overall_errors += 1

    if overall_errors > 0:
        print(f"\nTotal Errors: {overall_errors}")
        sys.exit(1)
    else:
        print("\nOK: Documentation is consistent.")
        sys.exit(0)

if __name__ == "__main__":
    main()
