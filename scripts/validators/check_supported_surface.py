#!/usr/bin/env python3
# Owner: platform-ops
import os
import sys
import re

import yaml

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

ALLOWED_TIERS = [
    "production_core",
    "production_optional",
    "beta",
    "experimental",
    "internal",
    "deprecated",
    "advisory",
    "non-production"
]

def main():
    yaml_path = os.path.join(base_dir, "config/supported-surface.yaml")
    md_path = os.path.join(base_dir, "docs/PRODUCT_SURFACE.md")
    
    if not os.path.exists(yaml_path):
        print(f"FAIL: config/supported-surface.yaml not found at {yaml_path}")
        sys.exit(1)
        
    if not os.path.exists(md_path):
        print(f"FAIL: docs/PRODUCT_SURFACE.md not found at {md_path}")
        sys.exit(1)
        
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception as e:
        print(f"FAIL: Error reading config/supported-surface.yaml: {e}")
        sys.exit(1)

    try:
        with open(md_path, "r", encoding="utf-8") as f:
            md_content = f.read()
    except Exception as e:
        print(f"FAIL: Error reading docs/PRODUCT_SURFACE.md: {e}")
        sys.exit(1)

    capabilities = data.get("capabilities", [])
    if not isinstance(capabilities, list):
        print("FAIL: 'capabilities' root key must be a list.")
        sys.exit(1)

    errors = []
    status_counts = {tier: 0 for tier in ALLOWED_TIERS}
    status_counts["unknown"] = 0
    
    md_content_lower = md_content.lower()
    
    # Validation loop
    for cap in capabilities:
        cap_id = cap.get("id", "UNNAMED")
        cap_name = cap.get("name", cap_id)
        cap_status = cap.get("status")
        
        # 1. Owner check
        if not cap.get("owner"):
            errors.append(f"Capability '{cap_id}' has no 'owner' defined.")
            
        # 2. Support Level check
        if not cap.get("support_level"):
            errors.append(f"Capability '{cap_id}' has no 'support_level' defined.")
            
        # 3. Status check
        if cap_status not in ALLOWED_TIERS:
            errors.append(f"Capability '{cap_id}' has invalid status '{cap_status}'. Allowed: {ALLOWED_TIERS}")
            status_counts["unknown"] += 1
        else:
            status_counts[cap_status] += 1
            
        # 4. Sync with PRODUCT_SURFACE.md check
        # Check if the name or ID appears in the Markdown table
        if cap_name.lower() not in md_content_lower and cap_id.lower() not in md_content_lower:
            errors.append(f"Capability '{cap_name}' ({cap_id}) is missing from docs/PRODUCT_SURFACE.md")

    # Check for legacy/simulated claims in MD that might be missing in YAML (optional but good)
    # For now, focus on YAML as source of truth for CI gate.

    if errors:
        print("\nPolicy Violations Found in Supported Surface Governance:")
        for err in errors:
            print(f" - [VIOLATION] {err}")
        sys.exit(1)
        
    print(f"\nPASS: Supported surface validation passed for all {len(capabilities)} capabilities.")
    print("Status Summary:")
    for tier, count in status_counts.items():
        if count > 0:
            print(f" - {tier}: {count}")
    sys.exit(0)

if __name__ == "__main__":
    main()
