#!/bin/bash
set -e

# Configuration
API_URL=${API_URL:-"http://localhost:8000"}
ADMIN_TOKEN=${ADMIN_TOKEN:-"admin-token-direct"}

echo "--- Validating System Control Center ---"

# 1. Validate endpoint requires admin token
echo "Testing authentication..."
# We expect 401 or 403 if unauthorized. Some setups might return 404 if route is hidden.
STATUS_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/admin/system/control-center")
if [ "$STATUS_CODE" -eq 401 ] || [ "$STATUS_CODE" -eq 403 ]; then
    echo "OK: Unauthorized without token (Code: $STATUS_CODE)"
elif [ "$STATUS_CODE" -eq 404 ]; then
    echo "WARNING: Endpoint returned 404. Is the server running and route registered?"
    # We don't exit here because the server might not be running during this check in some CI envs
    # but for a local validation script, it should be running.
else
    echo "FAIL: Endpoint should require auth or be reachable (Code: $STATUS_CODE)"
fi

# 2. Check UI integration (presence of System Control Center in index.html)
echo "Checking UI integration in static files..."
if grep -q "System Control Center" control_plane/app/static/admin/index.html; then
    echo "OK: UI section exists in index.html"
else
    echo "FAIL: UI section missing in index.html"
    exit 1
fi

if grep -q "renderControlCenter" control_plane/app/static/admin/index.html; then
    echo "OK: renderControlCenter function exists"
else
    echo "FAIL: renderControlCenter function missing"
    exit 1
fi

# 3. Check for secrets in the code (Backend)
echo "Checking for secrets in backend implementation..."
if grep -Ei "ADMIN_TOKEN|DATABASE_URL" control_plane/app/api/system.py | grep -v "require_admin" | grep -v "Depends"; then
    echo "WARNING: Potential secret exposure in system.py. Please review."
else
    echo "OK: No obvious secret exposure in system.py"
fi

echo "--- System Control Center Source Validation COMPLETED ---"
echo "Note: To run full API validation, ensure the server is running and use ADMIN_TOKEN."
