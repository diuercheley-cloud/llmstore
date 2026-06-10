#!/usr/bin/env python3
import os
import re
import sys


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
    print("--- Phase 72 Validation: Approval-Gated Remediation Execution ---\n")
    
    files_to_check = [
        "control_plane/app/models/operations/remediation_execution.py",
        "control_plane/app/services/operations/remediation_execution/execution_gate.py",
        "control_plane/app/services/operations/remediation_execution/simulation_adapter.py",
        "control_plane/app/services/operations/remediation_execution/executor.py",
        "control_plane/app/services/operations/remediation_execution/rollback.py",
        "control_plane/app/services/operations/remediation_execution/receipts.py",
        "control_plane/app/services/operations/remediation_execution/audit_events.py",
        "control_plane/app/api/operations_remediation_execution_admin.py",
        "docs/phases/phase_72_approval_gated_remediation_execution.md",
        "docs/operations/remediation_execution.md",
        "docs/operations/phase_72_remediation_execution_summary.md"
    ]
    
    all_files_present = all(check_file(f) for f in files_to_check)
    
    print("\n--- Content Validation ---")
    
    api_patterns = {
        "Router registered": "router = APIRouter",
        "Tenant isolation": "client_id",
        "Prepare endpoint": "@router.post\\(\"/prepare\"\\)",
        "Execute endpoint": "@router.post\\(\"/execute\"\\)",
        "Kill-switch endpoint": "@router.post\\(\"/kill-switch\"\\)"
    }
    api_ok = check_content("control_plane/app/api/operations_remediation_execution_admin.py", api_patterns)
    
    gate_patterns = {
        "Approval check": "verify_approval",
        "Kill-switch check": "verify_kill_switch",
        "Rollback check": "verify_rollback_plan",
        "Blast radius check": "verify_blast_radius"
    }
    gate_ok = check_content("control_plane/app/services/operations/remediation_execution/execution_gate.py", gate_patterns)
    
    print("\n--- Forbidden Patterns Check ---")
    
    forbidden = {
        "random usage": "random\\.",
        "external network": "requests\\.|httpx\\.|urllib",
        "subprocess": "subprocess\\.|os\\.system",
        "external ML calls": "openai|anthropic|cohere|langchain",
        "real infra execution": "kubernetes\\.|boto3\\.|proxmox"
    }
    
    services_to_check = [
        "control_plane/app/services/operations/remediation_execution/simulation_adapter.py",
        "control_plane/app/services/operations/remediation_execution/executor.py",
        "control_plane/app/services/operations/remediation_execution/execution_gate.py"
    ]
    
    forbidden_ok = all(check_forbidden(f, forbidden) for f in services_to_check)
    
    print("\n--- Dashboard Check ---")
    dashboard_patterns = {
        "Phase 72 Marker": "Approval-Gated Remediation Execution",
        "Phase 72 Status": "Simulation-only in Phase 72"
    }
    admin_dashboard_ok = check_content("control_plane/app/static/admin/index.html", dashboard_patterns)
    portal_dashboard_ok = check_content("control_plane/app/static/portal/index.html", dashboard_patterns)
    
    if all_files_present and api_ok and gate_ok and forbidden_ok and admin_dashboard_ok and portal_dashboard_ok:
        print("\n✅ PHASE 72 VALIDATION SUCCESSFUL")
        sys.exit(0)
    else:
        print("\n❌ PHASE 72 VALIDATION FAILED")
        sys.exit(1)

if __name__ == "__main__":
    main()
