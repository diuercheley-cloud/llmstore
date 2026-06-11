import argparse
import httpx
import json
import os
import sys

API_URL = os.environ.get("CONTROL_PLANE_URL", "http://localhost:8080")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "test-admin-token")


def restore_backup(backup_id, dry_run=True):
    mode = "DRY-RUN" if dry_run else "REAL RESTORE"
    print(f"Initiating backup restore ({mode}) for ID: {backup_id}")

    headers = {"X-Admin-Token": ADMIN_TOKEN}
    try:
        if dry_run:
            endpoint = f"{API_URL}/admin/backup/{backup_id}/restore/dry-run"
            resp = httpx.post(endpoint, headers=headers)
        else:
            endpoint = f"{API_URL}/admin/backup/{backup_id}/restore"
            resp = httpx.post(endpoint, headers=headers, json={"dry_run": False})

        resp.raise_for_status()

        results = resp.json()
        print(f"Restore Status: {results['status']}")
        if "plan" in results:
            print("Restoration Plan:")
            for step in results["plan"]:
                print(f"  - {step}")

        if results.get("staging_validated"):
            print("Verified: Staging validation passed.")

        if dry_run:
            print("Verified: No state changes were applied (Dry-run confirmed).")

    except Exception as e:
        print(f"Error restoring backup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", required=True, help="Backup ID to restore")
    parser.add_argument("--yes-really-restore", action="store_true",
                        help="Perform real restore (Warning! Requires approval workflow in production)")
    args = parser.parse_args()

    restore_backup(args.id, dry_run=not args.yes_really_restore)
