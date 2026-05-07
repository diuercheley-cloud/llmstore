#!/usr/bin/env bash
set -e

echo "Starting validation of Demo Admin Dashboard..."

source .venv/bin/activate || true
export PYTHONPATH="$PWD/control_plane:$PYTHONPATH"

cat << 'EOF' > validate_dashboard.py
import sys
import asyncio
from fastapi.testclient import TestClient
from app.main import app

def run_validation():
    # We rely on pytest to provide a full integration test environment
    import pytest
    code = pytest.main(["tests/test_demo_admin_dashboard.py", "tests/test_demo_admin_security.py", "-q"])
    if code != 0:
        print("Tests failed!")
        sys.exit(1)
        
    print("Checking if dashboard loads directly...")
    client = TestClient(app)
    resp = client.get("/static/admin/index.html")
    if resp.status_code != 200:
        print(f"Error: Could not load Admin Dashboard. Status: {resp.status_code}")
        sys.exit(1)
    print("Dashboard loaded OK.")

run_validation()
print("Validation passed.")
EOF

python validate_dashboard.py
rm validate_dashboard.py
