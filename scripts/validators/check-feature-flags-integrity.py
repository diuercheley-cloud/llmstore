#!/usr/bin/env python3
import os
import sys

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
sys.path.insert(0, os.path.join(base_dir, "control_plane"))

try:
    from app.services.platform.feature_flag_audit import FeatureFlagAuditService
except ImportError as e:
    print(f"Error: Could not import app modules. {e}")
    sys.exit(1)


def main():
    service = FeatureFlagAuditService()
    audit_results = service.perform_audit()

    failed = False

    # 1. Duplicates
    if audit_results["duplicates"]:
        print(f"FAIL: Duplicated flags found: {audit_results['duplicates']}")
        failed = True

    # 2. Missing Owner
    if audit_results["sem_owner"]:
        print(f"FAIL: Flags missing owner team: {audit_results['sem_owner']}")
        failed = True

    # 3. Missing Safe Default Reason
    if audit_results["sem_safe_default_reason"]:
        print(
            f"FAIL: Flags missing safe default reason: {audit_results['sem_safe_default_reason']}"
        )
        failed = True

    # 4. Missing Docs
    if audit_results["sem_docs"]:
        print(f"FAIL: Flags missing documentation: {audit_results['sem_docs']}")
        failed = True

    # 5. Active Conflicts
    if audit_results["active_conflicts"]:
        print(f"FAIL: Active conflicts detected: {audit_results['active_conflicts']}")
        failed = True

    # 6. Orphans are reported for visibility but do not fail the build.
    if audit_results["orphans"]:
        print(f"WARN: Orphaned flags detected: {audit_results['orphans']}")

    if failed:
        sys.exit(1)

    print("PASS: Feature Flag Integrity verified successfully.")
    sys.exit(0)


if __name__ == "__main__":
    main()
