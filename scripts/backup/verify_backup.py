import argparse
import httpx
import json
import os
import sys

API_URL = os.environ.get("CONTROL_PLANE_URL", "http://localhost:8000")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "test-admin-token")

def verify_backup(backup_id):
    print(f"Verifying backup integrity for ID: {backup_id}")
    
    headers = {"X-Admin-Token": ADMIN_TOKEN}
    try:
        resp = httpx.get(f"{API_URL}/api/admin/backup/{backup_id}/verify", headers=headers)
        resp.raise_for_status()
        
        results = resp.json()
        print(f"Status: {results['status'].upper()}")
        for comp in results.get("component_verification", []):
            print(f"  - {comp['name']}: {comp['status']}")
            
        if results["status"] == "valid":
            print("Integrity check PASSED.")
        else:
            print("Integrity check FAILED.")
            sys.exit(1)
            
    except Exception as e:
        print(f"Error verifying backup: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", required=True, help="Backup ID to verify")
    args = parser.parse_args()
    verify_backup(args.id)
