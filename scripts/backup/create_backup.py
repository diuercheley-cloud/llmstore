import argparse
import json
import os
import sys

import httpx

API_URL = os.environ.get("CONTROL_PLANE_URL", "http://localhost:8080")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "test-admin-token")


def create_backup(scope: str = "full"):
    print(f"Triggering backup creation via API: {API_URL}")

    headers = {"X-Admin-Token": ADMIN_TOKEN}
    payload = {"scope": scope} if scope != "full" else None
    try:
        resp = httpx.post(f"{API_URL}/admin/backup", headers=headers, json=payload, timeout=60.0)
        resp.raise_for_status()

        manifest = resp.json()
        print("Backup created successfully!")
        print(json.dumps(manifest, indent=2))

        filename = f"backup_{manifest['backup_id']}.json"
        with open(filename, "w") as f:
            json.dump(manifest, f, indent=2)
        print(f"Manifest saved to {filename}")

    except Exception as e:
        print(f"Error creating backup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a system backup via API")
    parser.add_argument(
        "--scope",
        default="full",
        choices=["full", "logical-agent-backup"],
        help="Backup scope (default: full)",
    )
    args = parser.parse_args()
    create_backup(scope=args.scope)
