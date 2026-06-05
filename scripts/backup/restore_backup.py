import argparse
import httpx
import json
import os
import sys

API_URL = os.environ.get("CONTROL_PLANE_URL", "http://localhost:8000")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "test-admin-token")

def restore_backup(backup_id, dry_run=True):
    mode = "DRY-RUN" if dry_run else "REAL RESTORE"
    print(f"Initiating backup restore ({mode}) for ID: {backup_id}")
    
    headers = {"X-Admin-Token": ADMIN_TOKEN}
    try:
        endpoint = f"/api/admin/backup/{backup_id}/restore/dry-run"
        if not dry_run:
            print("Error: Real restore not yet implemented in this foundation. Using dry-run.")
            
        resp = httpx.post(f"{API_URL}{endpoint}", headers=headers)
        resp.raise_for_status()
        
        results = resp.json()
        print(f"Restore Status: {results['status']}")
        print("Restoration Plan:")
        for step in results.get("plan", []):
            print(f"  - {step}")
            
        if results.get("side_effects_prevented"):
            print("Verified: No state changes were applied (Dry-run confirmed).")
            
    except Exception as e:
        print(f"Error restoring backup: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", required=True, help="Backup ID to restore")
    parser.add_argument("--yes-really-restore", action="store_true", help="Perform real restore (Warning!)")
    args = parser.parse_args()
    
    restore_backup(args.id, dry_run=not args.yes_really_restore)
