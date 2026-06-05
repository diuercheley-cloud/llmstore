import argparse
import httpx
import json
import os
import sys

API_URL = os.environ.get("CONTROL_PLANE_URL", "http://localhost:8000")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "test-admin-token")

def create_backup():
    print(f"Triggering backup creation via API: {API_URL}")
    
    headers = {"X-Admin-Token": ADMIN_TOKEN}
    try:
        resp = httpx.post(f"{API_URL}/api/admin/backup/create", headers=headers, timeout=60.0)
        resp.raise_for_status()
        
        manifest = resp.json()
        print("Backup created successfully!")
        print(json.dumps(manifest, indent=2))
        
        # Save manifest locally
        filename = f"backup_{manifest['backup_id']}.json"
        with open(filename, "w") as f:
            json.dump(manifest, f, indent=2)
        print(f"Manifest saved to {filename}")
        
    except Exception as e:
        print(f"Error creating backup: {e}")
        sys.exit(1)

if __name__ == "__main__":
    create_backup()
