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
    print("--- Phase 71 Validation: Deterministic Remediation Planning ---\n")
    
    files_to_check = [
        "control_plane/app/models/operations/remediation_planning.py",
        "control_plane/app/services/operations/remediation/deterministic_planner.py",
        "control_plane/app/services/operations/remediation/blast_radius.py",
        "control_plane/app/services/operations/remediation/approval_requirements.py",
        "control_plane/app/services/operations/remediation/receipts.py",
        "control_plane/app/services/operations/remediation/audit_events.py",
        "control_plane/app/api/operations_remediation_admin.py",
        "docs/phases/phase_71_deterministic_remediation_planning.md",
        "docs/operations/remediation_planning.md",
        "docs/operations/phase_71_remediation_planning_summary.md"
    ]
    
    all_files_present = all(check_file(f) for f in files_to_check)
    
    print("\n--- Content Validation ---")
    
    api_patterns = {
        "Router registered": "router = APIRouter",
        "Advisory only mandate": "advisory_only=True",
        "Dry run by default": "dry_run",
        "Tenant isolation": "client_id",
        "Propose endpoint": "@router.post\\(\"/propose\"\\)"
    }
    api_ok = check_content("control_plane/app/api/operations_remediation_admin.py", api_patterns)
    
    planner_patterns = {
        "Deterministic hash": "hashlib.sha256",
        "Normalize inputs": "normalize_inputs"
    }
    planner_ok = check_content("control_plane/app/services/operations/remediation/deterministic_planner.py", planner_patterns)
    
    print("\n--- Forbidden Patterns Check ---")
    
    forbidden = {
        "random usage": "random\\.",
        "uuid4 in logic": "uuid\\.uuid4\\(\\)",
        "external ML calls": "openai|anthropic|cohere|langchain",
        "external network": "requests\\.|httpx\\.|urllib",
        "automatic execution": "execute_remediation|run_action|apply_fix"
    }
    # We allow uuid4 for primary keys in models, so we only check services for uuid4
    services_to_check = [
        "control_plane/app/services/operations/remediation/deterministic_planner.py",
        "control_plane/app/services/operations/remediation/blast_radius.py",
        "control_plane/app/services/operations/remediation/approval_requirements.py"
    ]
    
    forbidden_ok = all(check_forbidden(f, forbidden) for f in services_to_check)
    
    print("\n--- Dashboard Check ---")
    dashboard_patterns = {
        "Phase 71 Marker": "Deterministic Remediation Planning",
        "Advisory Warning": "Planning only — no automatic remediation"
    }
    admin_dashboard_ok = check_content("control_plane/app/static/admin/index.html", dashboard_patterns)
    portal_dashboard_ok = check_content("control_plane/app/static/portal/index.html", dashboard_patterns)
    
    if all_files_present and api_ok and planner_ok and forbidden_ok and admin_dashboard_ok and portal_dashboard_ok:
        print("\n✅ PHASE 71 VALIDATION SUCCESSFUL")
        sys.exit(0)
    else:
        print("\n❌ PHASE 71 VALIDATION FAILED")
        sys.exit(1)

if __name__ == "__main__":
    main()
