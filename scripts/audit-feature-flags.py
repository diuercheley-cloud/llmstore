#!/usr/bin/env python3
import os
import sys
import argparse

# Ensure control_plane is in path
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
sys.path.insert(0, os.path.join(base_dir, "control_plane"))

try:
    from app.services.platform.feature_flag_audit import FeatureFlagAuditService
except ImportError as e:
    print(f"Error: Could not import app modules. {e}")
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Feature Flag Governance Audit Tool")
    parser.add_argument(
        "--fix",
        choices=["deprecate", "remove"],
        help="Automatically clean up orphaned flags by deprecating or removing them."
    )
    args = parser.parse_args()

    service = FeatureFlagAuditService()
    
    print("--- Running Feature Flag Governance Audit ---")
    audit_results = service.perform_audit()
    
    # Generate report
    report_path = service.generate_report(audit_results)
    print(f"Report generated successfully at: {report_path}")
    
    # Print summary
    print(f"\nAudit Summary:")
    print(f" - Total Registered Flags: {audit_results['total_registered']}")
    print(f" - Active: {len(audit_results['classification']['active'])}")
    print(f" - Experimental: {len(audit_results['classification']['experimental'])}")
    print(f" - Deprecated: {len(audit_results['classification']['deprecated'])}")
    print(f" - Orphaned: {len(audit_results['orphans'])}")
    print(f" - Internal Only: {len(audit_results['classification']['internal_only'])}")
    
    violations_found = False
    
    if audit_results["duplicates"]:
        print(f"\n[VIOLATION] Duplicated flags found: {', '.join(audit_results['duplicates'])}")
        violations_found = True
        
    if audit_results["sem_owner"]:
        print(f"\n[VIOLATION] Flags missing owner team: {', '.join(audit_results['sem_owner'])}")
        violations_found = True
        
    if audit_results["sem_safe_default_reason"]:
        print(f"\n[VIOLATION] Flags missing safe default reason: {', '.join(audit_results['sem_safe_default_reason'])}")
        violations_found = True

    if audit_results["sem_docs"]:
        print(f"\n[VIOLATION] Flags missing documentation (description/details): {', '.join(audit_results['sem_docs'])}")
        violations_found = True

    if audit_results["active_conflicts"]:
        print(f"\n[VIOLATION] Active conflicts detected:")
        for conflict in audit_results["active_conflicts"]:
            print(f"   - {conflict['message']}")
        violations_found = True

    if audit_results["orphans"]:
        print(f"\n[WARNING] Orphaned flags detected ({len(audit_results['orphans'])} flags). Use --fix deprecate/remove to cleanup.")

    # Perform cleanup if --fix is set
    if args.fix:
        print(f"\n--- Running Cleanup (mode: {args.fix}) ---")
        count, modified = service.cleanup_orphaned_flags(mode=args.fix)
        print(f"Successfully modified/cleaned {count} orphaned flags.")
        # Re-run audit to update report after cleanup
        new_results = service.perform_audit()
        service.generate_report(new_results)
        print("Updated audit report generated after cleanup.")
    
    if violations_found:
        print("\nFAIL: Feature Flag Governance policy violations found.")
        sys.exit(1)
    else:
        print("\nPASS: Feature Flag Governance audit completed.")
        sys.exit(0)

if __name__ == "__main__":
    main()
