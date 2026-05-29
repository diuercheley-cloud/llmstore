#!/usr/bin/env python3
# Owner: platform-ops
import os
import sys
import yaml

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))

def main():
    yaml_path = os.path.join(base_dir, "config/supported-surface.yaml")
    if not os.path.exists(yaml_path):
        print(f"FAIL: config/supported-surface.yaml not found at {yaml_path}")
        sys.exit(1)
        
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception as e:
        print(f"FAIL: Error reading config/supported-surface.yaml: {e}")
        sys.exit(1)

    capabilities = data.get("capabilities", [])
    if not isinstance(capabilities, list):
        print("FAIL: 'capabilities' root key must be a list.")
        sys.exit(1)

    errors = []
    
    # Validation loop
    for cap in capabilities:
        cap_id = cap.get("id", "UNNAMED")
        
        # 1. Owner check
        if not cap.get("owner"):
            errors.append(f"Capability '{cap_id}' has no 'owner' defined.")
            
        # 2. Support Level check
        if not cap.get("support_level"):
            errors.append(f"Capability '{cap_id}' has no 'support_level' defined.")
            
        # 3. Docs URL check
        if not cap.get("docs_url"):
            errors.append(f"Capability '{cap_id}' has no 'docs_url' defined.")
            
        # 4. Rollback Story check
        if not cap.get("rollback_story"):
            errors.append(f"Capability '{cap_id}' has no 'rollback_story' defined.")

    if errors:
        print("\nPolicy Violations Found in supported-surface.yaml:")
        for err in errors:
            print(f" - [VIOLATION] {err}")
        sys.exit(1)
        
    print(f"PASS: Supported surface validation passed for all {len(capabilities)} capabilities.")
    sys.exit(0)

if __name__ == "__main__":
    main()
