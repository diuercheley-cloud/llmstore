#!/usr/bin/env python3
import os
import sys

# Ensure control_plane is in path to import app modules
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
sys.path.insert(0, os.path.join(base_dir, "control_plane"))

try:
    from app.services.feature_flag_registry import FeatureFlagRegistryService
except ImportError as e:
    print(f"Error: Could not import app modules. {e}")
    sys.exit(1)

def main():
    service = FeatureFlagRegistryService()
    
    print("--- Running Feature Flag Registry Policy Validation ---")
    is_valid, errors = service.validate_registry()
    failed = False
    
    if not is_valid:
        print("\nPolicy Violations Found:")
        for err in errors:
            print(f" - [VIOLATION] {err}")
        failed = True
    else:
        print("OK: Registry structure and policies are compliant.")
        
    print("\n--- Scanning for Orphaned and Unregistered Flags ---")
    scan_results = service.scan_orphans()
    
    missing = scan_results.get("missing_registration", [])
    if missing:
        print("\nMissing Registrations (found in code or .env.example but not in registry):")
        for flag in sorted(missing):
            print(f" - [MISSING] {flag}")
        failed = True
    else:
        print("OK: All code and configuration flags are registered.")
        
    orphans = scan_results.get("orphans", [])
    print(f"\n--- Orphaned Flags Report ({len(orphans)} flags) ---")
    if orphans:
        print("The following registered flags are not referenced in python code or env:")
        for flag in sorted(orphans):
            print(f" - [ORPHAN] {flag}")
    else:
        print("No orphaned flags detected.")
        
    print(f"\nSummary:")
    print(f" - Registered: {scan_results.get('registered_count')}")
    print(f" - Env references: {scan_results.get('env_references_count')}")
    print(f" - Code references (approx): {scan_results.get('code_references_count')}")
    
    if failed:
        print("\nFAIL: Feature Flag Governance validation failed.")
        sys.exit(1)
    else:
        print("\nPASS: Feature Flag Governance validation passed.")
        sys.exit(0)

if __name__ == "__main__":
    main()
