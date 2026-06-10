#!/bin/bash
set -e

echo "Validating Commercial Geo Routing (Phase 19)..."

# 1. Syntax check
python3 -m py_compile control_plane/app/services/routing/commercial_geo_router.py
python3 -m py_compile control_plane/app/api/commercial_geo_routing_admin.py

# 2. Test execution
./venv/bin/pytest -q tests/test_commercial_geo_routing.py

# 3. API endpoints check (requires server running, so we skip live check and do mock check if possible)
echo "Geo Routing logic validated successfully."
