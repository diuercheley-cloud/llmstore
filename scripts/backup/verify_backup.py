import argparse
import os
import sys

import httpx

API_URL = os.environ.get("CONTROL_PLANE_URL", "http://localhost:8080")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "test-admin-token")


def verify_backup(backup_id: str):
    print(f"Verifying backup integrity for ID: {backup_id}")

    headers = {"X-Admin-Token": ADMIN_TOKEN}
    try:
        resp = httpx.post(
            f"{API_URL}/admin/backup/{backup_id}/verify",
            headers=headers,
            timeout=60.0,
        )
        resp.raise_for_status()
        result = resp.json()
        if result.get("valid"):
            print(f"Backup {backup_id} integrity: VALID")
            if "checksum" in result:
                print(f"Checksum: {result['checksum']}")
        else:
            print(f"Backup {backup_id} integrity: INVALID")
            if "errors" in result:
                for err in result["errors"]:
                    print(f"  - {err}")
            sys.exit(1)
    except Exception as e:
        print(f"Error verifying backup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify backup integrity via API")
    parser.add_argument("--id", required=True, help="Backup ID to verify")
    args = parser.parse_args()
    verify_backup(args.id)
