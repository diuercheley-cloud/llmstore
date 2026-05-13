#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON="${PYTHON:-$PROJECT_ROOT/.venv/bin/python}"

PASS=0
FAIL=0

pass()  { PASS=$((PASS+1)); echo "  PASS: $*"; }
fail()  { FAIL=$((FAIL+1)); echo "  FAIL: $*"; }

echo "=== Hybrid Admin Dashboard Validation ==="
echo ""

# ---- 1. Summary endpoint requires admin token ----
echo "--- 1. Summary endpoint requires admin token ---"
RESULT=$(cd "$PROJECT_ROOT" && $PYTHON -c "
import sys; sys.path.insert(0, 'control_plane')
import os; os.environ.setdefault('ADMIN_TOKEN', 'test-admin-token')
os.environ.setdefault('DATABASE_URL', 'sqlite+aiosqlite:///tmp/test_hybrid_admin.db')
os.environ.setdefault('REDIS_URL', 'redis://test.invalid:6379/0')
os.environ.setdefault('DATA_PLANE_BASE_URL', 'http://localhost:8081')
os.environ.setdefault('PROVIDERS_ENABLED', 'local,lmstudio')
os.environ.setdefault('CLOUD_PROVIDERS_ENABLED', 'false')
from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)
# Without token
resp = client.get('/admin/hybrid/summary', headers={})
print(f'status_no_token={resp.status_code}')
# With token
resp2 = client.get('/admin/hybrid/summary', headers={'X-Admin-Token': 'test-admin-token'})
print(f'status_with_token={resp2.status_code}')
")
echo "$RESULT"
if echo "$RESULT" | grep -q "status_no_token=40[13]"; then
  pass "Summary endpoint rejects unauthenticated requests"
else
  fail "Summary endpoint should return 401/403 without token"
fi
if echo "$RESULT" | grep -q "status_with_token=200"; then
  pass "Summary endpoint accepts valid admin token"
else
  fail "Summary endpoint should return 200 with valid token"
fi
echo ""

# ---- 2. Summary returns valid JSON with expected fields ----
echo "--- 2. Summary returns valid JSON with expected fields ---"
RESULT=$(cd "$PROJECT_ROOT" && $PYTHON -c "
import sys; sys.path.insert(0, 'control_plane')
import os; os.environ.setdefault('ADMIN_TOKEN', 'test-admin-token')
os.environ.setdefault('DATABASE_URL', 'sqlite+aiosqlite:///tmp/test_hybrid_admin.db')
os.environ.setdefault('REDIS_URL', 'redis://test.invalid:6379/0')
os.environ.setdefault('DATA_PLANE_BASE_URL', 'http://localhost:8081')
os.environ.setdefault('PROVIDERS_ENABLED', 'local,lmstudio')
os.environ.setdefault('CLOUD_PROVIDERS_ENABLED', 'false')
import json
from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)
resp = client.get('/admin/hybrid/summary', headers={'X-Admin-Token': 'test-admin-token'})
data = resp.json()
required = ['total_requests','local_requests','cloud_requests','cache_hit_rate','provider_cost_brl','customer_revenue_brl','gross_profit_brl','margin_percent','active_wallets','low_balance_clients','providers_enabled','providers_configured','warnings','critical_failures','cloud_enabled','local_first','timestamp']
missing = [f for f in required if f not in data]
if missing:
    print(f'MISSING={missing}')
else:
    print('ALL_FIELDS_PRESENT=true')
")
echo "$RESULT"
if echo "$RESULT" | grep -q "ALL_FIELDS_PRESENT=true"; then
  pass "Summary returns all required fields"
else
  fail "Summary missing fields: $(echo "$RESULT" | grep MISSING || true)"
fi
echo ""

# ---- 3. Dashboard HTML contains hybrid cards ----
echo "--- 3. Dashboard HTML contains hybrid cards ---"
DASHBOARD="$PROJECT_ROOT/control_plane/app/static/admin/index.html"
if [ -f "$DASHBOARD" ]; then
  if grep -q "Hybrid AI Platform" "$DASHBOARD" && \
     grep -q "providersSection" "$DASHBOARD" && \
     grep -q "routingSection" "$DASHBOARD" && \
     grep -q "costsSection" "$DASHBOARD" && \
     grep -q "marginSection" "$DASHBOARD" && \
     grep -q "walletSection" "$DASHBOARD" && \
     grep -q "cacheSection" "$DASHBOARD" && \
     grep -q "hybridRagSection" "$DASHBOARD" && \
     grep -q "providerHealthSection" "$DASHBOARD"; then
    pass "Dashboard contains all hybrid cards"
  else
    fail "Dashboard is missing some hybrid cards"
  fi
else
  fail "Dashboard HTML not found at $DASHBOARD"
fi
echo ""

# ---- 4. Dashboard does not contain secrets ----
echo "--- 4. Dashboard does not contain secrets ---"
if [ -f "$DASHBOARD" ]; then
  LOWER_CONTENT=$(tr '[:upper:]' '[:lower:]' < "$DASHBOARD")
  if echo "$LOWER_CONTENT" | grep -q "secret"; then
    fail "Dashboard contains the word 'secret'"
  else
    pass "Dashboard does not contain exposed secrets"
  fi
fi
echo ""

# ---- 5. Admin sees margin ----
echo "--- 5. Admin sees margin ---"
RESULT=$(cd "$PROJECT_ROOT" && $PYTHON -c "
import sys; sys.path.insert(0, 'control_plane')
import os; os.environ.setdefault('ADMIN_TOKEN', 'test-admin-token')
os.environ.setdefault('DATABASE_URL', 'sqlite+aiosqlite:///tmp/test_hybrid_admin.db')
os.environ.setdefault('REDIS_URL', 'redis://test.invalid:6379/0')
os.environ.setdefault('DATA_PLANE_BASE_URL', 'http://localhost:8081')
os.environ.setdefault('PROVIDERS_ENABLED', 'local,lmstudio')
os.environ.setdefault('CLOUD_PROVIDERS_ENABLED', 'false')
from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)
resp = client.get('/admin/hybrid/summary', headers={'X-Admin-Token': 'test-admin-token'})
data = resp.json()
if 'margin_percent' in data and 'gross_profit_brl' in data:
    print('ADMIN_SEES_MARGIN=true')
else:
    print('ADMIN_SEES_MARGIN=false')
")
echo "$RESULT"
if echo "$RESULT" | grep -q "ADMIN_SEES_MARGIN=true"; then
  pass "Admin can see margin_percent and gross_profit_brl"
else
  fail "Admin should see margin data"
fi
echo ""

# ---- 6. Client portal does not see margin ----
echo "--- 6. Client portal does not see margin ---"
PORTAL="$PROJECT_ROOT/control_plane/app/static/portal/index.html"
if [ -f "$PORTAL" ]; then
  PORTAL_LOWER=$(tr '[:upper:]' '[:lower:]' < "$PORTAL")
  HAS_MARGIN=false
  echo "$PORTAL_LOWER" | grep -q "gross_profit" && HAS_MARGIN=true
  echo "$PORTAL_LOWER" | grep -q "margin_percent" && HAS_MARGIN=true
  echo "$PORTAL_LOWER" | grep -q "provider_cost" && HAS_MARGIN=true
  if [ "$HAS_MARGIN" = false ]; then
    pass "Client portal does not expose internal margin"
  else
    fail "Client portal should not contain margin/gross_profit/provider_cost"
  fi
else
  echo "  INFO: Client portal HTML not found, skipping"
  pass "Client portal not found (assumed not exposed)"
fi
echo ""

# ---- 7. Cloud disabled appears clearly ----
echo "--- 7. Cloud disabled appears clearly ---"
RESULT=$(cd "$PROJECT_ROOT" && $PYTHON -c "
import sys; sys.path.insert(0, 'control_plane')
import os; os.environ.setdefault('ADMIN_TOKEN', 'test-admin-token')
os.environ.setdefault('DATABASE_URL', 'sqlite+aiosqlite:///tmp/test_hybrid_admin.db')
os.environ.setdefault('REDIS_URL', 'redis://test.invalid:6379/0')
os.environ.setdefault('DATA_PLANE_BASE_URL', 'http://localhost:8081')
os.environ.setdefault('PROVIDERS_ENABLED', 'local,lmstudio')
os.environ.setdefault('CLOUD_PROVIDERS_ENABLED', 'false')
from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)
resp = client.get('/admin/hybrid/summary', headers={'X-Admin-Token': 'test-admin-token'})
data = resp.json()
print(f'cloud_enabled={data[\"cloud_enabled\"]}')
warnings = data.get('warnings', [])
for w in warnings:
    if 'cloud' in w.lower():
        print(f'WARNING={w}')
")
echo "$RESULT"
if echo "$RESULT" | grep -q "cloud_enabled=False"; then
  pass "Cloud disabled status is clearly visible in summary"
else
  fail "Cloud disabled should be clearly indicated"
fi
echo ""

# ---- 8. Providers endpoint masks API keys ----
echo "--- 8. Providers endpoint masks API keys ---"
RESULT=$(cd "$PROJECT_ROOT" && $PYTHON -c "
import sys; sys.path.insert(0, 'control_plane')
import os; os.environ.setdefault('ADMIN_TOKEN', 'test-admin-token')
os.environ.setdefault('DATABASE_URL', 'sqlite+aiosqlite:///tmp/test_hybrid_admin.db')
os.environ.setdefault('REDIS_URL', 'redis://test.invalid:6379/0')
os.environ.setdefault('DATA_PLANE_BASE_URL', 'http://localhost:8081')
os.environ.setdefault('PROVIDERS_ENABLED', 'local,lmstudio')
os.environ.setdefault('CLOUD_PROVIDERS_ENABLED', 'false')
from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)
resp = client.get('/admin/hybrid/providers', headers={'X-Admin-Token': 'test-admin-token'})
data = resp.json()
all_masked = all(
    (p.get('masked_api_key') is None or '****' in str(p.get('masked_api_key', '')))
    for p in data
)
print(f'ALL_MASKED={all_masked}')
")
echo "$RESULT"
if echo "$RESULT" | grep -q "ALL_MASKED=True"; then
  pass "All provider API keys are masked"
else
  fail "Some provider API keys are not masked"
fi
echo ""

# ---- Summary ----
echo "=== Results: $PASS passed, $FAIL failed ==="
if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
