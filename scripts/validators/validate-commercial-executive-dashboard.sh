#!/bin/bash
set -e

# Validation script for Phase 10: Executive Profitability and Drift Dashboard

echo "=== Validating Executive Profitability and Drift Dashboard ==="

# 1. Check if service file exists
if [ ! -f "control_plane/app/services/routing/commercial_executive_dashboard.py" ]; then
    echo "Error: Service file not found"
    exit 1
fi

# 2. Check if endpoints are registered (using grep on the file)
grep -q "/executive-dashboard/overview" control_plane/app/api/commercial_routing_admin.py || (echo "Error: /executive-dashboard/overview not found in API"; exit 1)
grep -q "/executive-dashboard/anomalies" control_plane/app/api/commercial_routing_admin.py || (echo "Error: /executive-dashboard/anomalies not found in API"; exit 1)
grep -q "/executive-dashboard/recommendations" control_plane/app/api/commercial_routing_admin.py || (echo "Error: /executive-dashboard/recommendations not found in API"; exit 1)

# 3. Check for documentation
if [ ! -f "docs/COMMERCIAL_EXECUTIVE_DASHBOARD.md" ]; then
    echo "Warning: docs/COMMERCIAL_EXECUTIVE_DASHBOARD.md not found (will be created soon)"
fi

# 4. Run tests
echo "Running tests..."
if [ -f ".venv/bin/pytest" ]; then
    ./.venv/bin/pytest -q tests/test_commercial_executive_dashboard.py || (echo "Error: Tests failed"; exit 1)
else
    pytest -q tests/test_commercial_executive_dashboard.py || (echo "Error: Tests failed"; exit 1)
fi

echo "=== Validation Successful ==="
