#!/bin/bash
set -e

echo "Validating Commercial Live Balancing (Phase 19)..."

# 1. Syntax check
python3 -m py_compile control_plane/app/services/routing/commercial_live_balancer.py
python3 -m py_compile control_plane/app/api/commercial_live_balancing_admin.py

# 2. Test execution
./venv/bin/pytest -q tests/test_commercial_live_balancing.py

echo "Live Balancing logic validated successfully."
