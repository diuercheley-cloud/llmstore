#!/usr/bin/env python3
import os
import sys
import re

def check_file(path):
    if os.path.exists(path):
        print(f"✅ Found: {path}")
        return True
    else:
        print(f"❌ Missing: {path}")
        return False

def check_content(path, patterns):
    if not os.path.exists(path):
        return False
    
    with open(path, 'r') as f:
        content = f.read()
    
    success = True
    for label, pattern in patterns.items():
        if re.search(pattern, content):
            print(f"✅ {label} present in {path}")
        else:
            print(f"❌ {label} NOT found in {path}")
            success = False
    return success

def check_forbidden(path, patterns):
    if not os.path.exists(path):
        return True
    
    with open(path, 'r') as f:
        content = f.read()
    
    success = True
    for label, pattern in patterns.items():
        if re.search(pattern, content):
            print(f"❌ FORBIDDEN {label} found in {path}")
            success = False
        else:
            print(f"✅ No forbidden {label} in {path}")
    return success

def main():
    print("--- Phase 73 Validation: Controlled Adapter Sandbox ---\n")
    
    files_to_check = [
        "control_plane/app/models/operations/adapter_sandbox.py",
        "control_plane/app/services/operations/adapter_sandbox/contracts.py",
        "control_plane/app/services/operations/adapter_sandbox/manifest_validator.py",
        "control_plane/app/services/operations/adapter_sandbox/simulation_runner.py",
        "control_plane/app/services/operations/adapter_sandbox/policy_guard.py",
        "control_plane/app/api/operations_adapter_sandbox_admin.py",
        "docs/phases/phase_73_controlled_adapter_sandbox.md",
        "docs/operations/adapter_sandbox.md",
        "docs/operations/phase_73_adapter_sandbox_summary.md"
    ]
    
    all_files_present = all(check_file(f) for f in files_to_check)
    
    print("\n--- Content Validation ---")
    
    api_patterns = {
        "Router registered": "router = APIRouter",
        "Manifest endpoint": "@router.post\\(\"/manifests\"\\)",
        "Simulate endpoint": "@router.post\\(\"/runs/simulate\"\\)",
        "Tenant isolation": "client_id"
    }
    api_ok = check_content("control_plane/app/api/operations_adapter_sandbox_admin.py", api_patterns)
    
    validator_patterns = {
        "Forbidden capabilities": "FORBIDDEN_CAPABILITIES",
        "Deterministic hash": "hashlib.sha256",
        "Sandbox requirement": "sandbox_required"
    }
    validator_ok = check_content("control_plane/app/services/operations/adapter_sandbox/manifest_validator.py", validator_patterns)
    
    print("\n--- Forbidden Patterns Check ---")
    
    forbidden = {
        "random usage": "random\\.",
        "external network": "requests\\.|httpx\\.|urllib|socket\\.",
        "subprocess": "subprocess\\.|os\\.system",
        "external ML calls": "openai|anthropic|cohere|langchain",
        "real infra execution": "kubernetes\\.|boto3\\.|proxmox"
    }
    
    services_to_check = [
        "control_plane/app/services/operations/adapter_sandbox/simulation_runner.py",
        "control_plane/app/services/operations/adapter_sandbox/manifest_validator.py",
        "control_plane/app/services/operations/adapter_sandbox/policy_guard.py"
    ]
    
    forbidden_ok = all(check_forbidden(f, forbidden) for f in services_to_check)
    
    print("\n--- Dashboard Check ---")
    dashboard_patterns = {
        "Phase 73 Marker": "Controlled Adapter Sandbox",
        "Sandbox Warning": "sandbox simulation only"
    }
    admin_dashboard_ok = check_content("control_plane/app/static/admin/index.html", dashboard_patterns)
    portal_dashboard_ok = check_content("control_plane/app/static/portal/index.html", dashboard_patterns)
    
    if all_files_present and api_ok and validator_ok and forbidden_ok and admin_dashboard_ok and portal_dashboard_ok:
        print("\n✅ PHASE 73 VALIDATION SUCCESSFUL")
        sys.exit(0)
    else:
        print("\n❌ PHASE 73 VALIDATION FAILED")
        sys.exit(1)

if __name__ == "__main__":
    main()
