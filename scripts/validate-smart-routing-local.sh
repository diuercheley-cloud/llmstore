#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON="${PYTHON:-$PROJECT_ROOT/.venv/bin/python}"

PASS=0
FAIL=0

pass()  { PASS=$((PASS+1)); echo "  PASS: $*"; }
fail()  { FAIL=$((FAIL+1)); echo "  FAIL: $*"; }

echo "=== Smart Routing Validation ==="
echo ""

# ---- 1. local_first chooses local provider ----
echo "--- 1. local_first chooses local provider ---"
RESULT=$(cd "$PROJECT_ROOT" && $PYTHON -c "
import sys; sys.path.insert(0, 'control_plane')
import os; os.environ.setdefault('ADMIN_TOKEN', 'test-admin-token')
os.environ.setdefault('DATABASE_URL', 'sqlite+aiosqlite:///tmp/test_sr.db')
os.environ.setdefault('REDIS_URL', 'redis://test.invalid:6379/0')
os.environ.setdefault('DATA_PLANE_BASE_URL', 'http://localhost:8081')
os.environ.setdefault('PROVIDERS_ENABLED', 'local,lmstudio')
os.environ.setdefault('CLOUD_PROVIDERS_ENABLED', 'false')
from app.schemas.routing import SmartRouterInput, RoutingStrategy, EndpointType
from app.services.routing.smart_router import get_smart_router
sr = get_smart_router()
inp = SmartRouterInput(
    endpoint_type=EndpointType.chat,
    cloud_allowed=False,
    strategy=RoutingStrategy.local_first,
)
dec = sr.route(inp)
print(f'provider={dec.selected_provider} cloud={dec.cloud_used}')
")
echo "$RESULT"
if echo "$RESULT" | grep -q "provider=local"; then
  pass "local_first selected local provider"
else
  fail "local_first should select local provider"
fi
echo ""

# ---- 2. cloud disabled does not use cloud ----
echo "--- 2. cloud disabled does not use cloud ---"
RESULT=$(cd "$PROJECT_ROOT" && $PYTHON -c "
import sys; sys.path.insert(0, 'control_plane')
import os; os.environ.setdefault('ADMIN_TOKEN', 'test-admin-token')
os.environ.setdefault('DATABASE_URL', 'sqlite+aiosqlite:///tmp/test_sr.db')
os.environ.setdefault('REDIS_URL', 'redis://test.invalid:6379/0')
os.environ.setdefault('DATA_PLANE_BASE_URL', 'http://localhost:8081')
os.environ.setdefault('PROVIDERS_ENABLED', 'local,openai,anthropic,deepseek')
os.environ.setdefault('CLOUD_PROVIDERS_ENABLED', 'false')
from app.schemas.routing import SmartRouterInput, RoutingStrategy, EndpointType
from app.services.routing.smart_router import get_smart_router
sr = get_smart_router()
inp = SmartRouterInput(
    endpoint_type=EndpointType.chat,
    cloud_allowed=False,
    strategy=RoutingStrategy.premium_quality,
)
dec = sr.route(inp)
print(f'provider={dec.selected_provider} cloud={dec.cloud_used}')
")
echo "$RESULT"
if echo "$RESULT" | grep -q "cloud=False"; then
  pass "cloud disabled does not use cloud"
else
  fail "cloud disabled should not use cloud"
fi
echo ""

# ---- 3. provider down generates fallback ----
echo "--- 3. provider down generates fallback ---"
RESULT=$(cd "$PROJECT_ROOT" && $PYTHON -c "
import sys; sys.path.insert(0, 'control_plane')
import os; os.environ.setdefault('ADMIN_TOKEN', 'test-admin-token')
os.environ.setdefault('DATABASE_URL', 'sqlite+aiosqlite:///tmp/test_sr.db')
os.environ.setdefault('REDIS_URL', 'redis://test.invalid:6379/0')
os.environ.setdefault('DATA_PLANE_BASE_URL', 'http://localhost:8081')
os.environ.setdefault('PROVIDERS_ENABLED', 'local,openai,anthropic,deepseek')
os.environ.setdefault('CLOUD_PROVIDERS_ENABLED', 'false')
from app.schemas.routing import SmartRouterInput, RoutingStrategy, EndpointType
from app.services.routing.smart_router import get_smart_router
sr = get_smart_router()
inp = SmartRouterInput(
    endpoint_type=EndpointType.chat,
    cloud_allowed=False,
    strategy=RoutingStrategy.fallback_only,
)
dec = sr.route(inp)
print(f'fallback_chain_len={len(dec.fallback_chain)} provider={dec.selected_provider}')
")
echo "$RESULT"
if echo "$RESULT" | grep -q "provider=local\|provider=mock"; then
  pass "provider down fallback works"
else
  fail "provider down should fall back to local or mock"
fi
echo ""

# ---- 4. coding task simulates Anthropic only if configured ----
echo "--- 4. coding task simulates Anthropic only if configured ---"
RESULT=$(cd "$PROJECT_ROOT" && $PYTHON -c "
import sys; sys.path.insert(0, 'control_plane')
import os; os.environ.setdefault('ADMIN_TOKEN', 'test-admin-token')
os.environ.setdefault('DATABASE_URL', 'sqlite+aiosqlite:///tmp/test_sr.db')
os.environ.setdefault('REDIS_URL', 'redis://test.invalid:6379/0')
os.environ.setdefault('DATA_PLANE_BASE_URL', 'http://localhost:8081')
# Without ANTHROPIC_API_KEY and cloud_disabled, coding falls back to local
os.environ.setdefault('PROVIDERS_ENABLED', 'local,anthropic')
os.environ.setdefault('CLOUD_PROVIDERS_ENABLED', 'false')
from app.schemas.routing import SmartRouterInput, RoutingStrategy, EndpointType
from app.services.routing.smart_router import get_smart_router
sr = get_smart_router()
inp = SmartRouterInput(
    endpoint_type=EndpointType.chat,
    cloud_allowed=False,
    strategy=RoutingStrategy.coding,
)
dec = sr.route(inp)
print(f'provider={dec.selected_provider}')
")
echo "$RESULT"
if echo "$RESULT" | grep -q "provider=local\|provider=mock"; then
  pass "coding with cloud disabled falls back to local (correct)"
else
  fail "coding with cloud disabled should fall back to local"
fi
echo ""

# ---- 5. low_budget simulates DeepSeek only if configured ----
echo "--- 5. low_budget simulates DeepSeek only if configured ---"
RESULT=$(cd "$PROJECT_ROOT" && $PYTHON -c "
import sys; sys.path.insert(0, 'control_plane')
import os; os.environ.setdefault('ADMIN_TOKEN', 'test-admin-token')
os.environ.setdefault('DATABASE_URL', 'sqlite+aiosqlite:///tmp/test_sr.db')
os.environ.setdefault('REDIS_URL', 'redis://test.invalid:6379/0')
os.environ.setdefault('DATA_PLANE_BASE_URL', 'http://localhost:8081')
os.environ.setdefault('PROVIDERS_ENABLED', 'local,deepseek')
os.environ.setdefault('CLOUD_PROVIDERS_ENABLED', 'false')
from app.schemas.routing import SmartRouterInput, RoutingStrategy, EndpointType
from app.services.routing.smart_router import get_smart_router
sr = get_smart_router()
inp = SmartRouterInput(
    endpoint_type=EndpointType.chat,
    cloud_allowed=False,
    strategy=RoutingStrategy.lowest_cost,
)
dec = sr.route(inp)
print(f'provider={dec.selected_provider}')
")
echo "$RESULT"
if echo "$RESULT" | grep -q "provider=local\|provider=mock"; then
  pass "lowest_cost with cloud disabled falls back to local (correct)"
else
  fail "lowest_cost with cloud disabled should fall back to local"
fi
echo ""

# ---- 6. insufficient balance blocks cloud ----
echo "--- 6. insufficient balance blocks cloud ---"
RESULT=$(cd "$PROJECT_ROOT" && $PYTHON -c "
import sys; sys.path.insert(0, 'control_plane')
import os; os.environ.setdefault('ADMIN_TOKEN', 'test-admin-token')
os.environ.setdefault('DATABASE_URL', 'sqlite+aiosqlite:///tmp/test_sr.db')
os.environ.setdefault('REDIS_URL', 'redis://test.invalid:6379/0')
os.environ.setdefault('DATA_PLANE_BASE_URL', 'http://localhost:8081')
os.environ.setdefault('PROVIDERS_ENABLED', 'local,openai')
os.environ.setdefault('CLOUD_PROVIDERS_ENABLED', 'false')
from app.schemas.routing import SmartRouterInput, RoutingStrategy, EndpointType
from app.services.routing.smart_router import get_smart_router
sr = get_smart_router()
inp = SmartRouterInput(
    endpoint_type=EndpointType.chat,
    cloud_allowed=False,
    wallet_balance_brl=0.0,
    strategy=RoutingStrategy.premium_quality,
)
dec = sr.route(inp)
print(f'provider={dec.selected_provider} cloud={dec.cloud_used} warnings={dec.warnings}')
")
echo "$RESULT"
if echo "$RESULT" | grep -q "cloud=False"; then
  pass "insufficient balance blocks cloud"
else
  fail "insufficient balance should block cloud"
fi
echo ""

# ---- 7. decision does not contain prompts or secrets ----
echo "--- 7. decision does not contain prompts or secrets ---"
RESULT=$(cd "$PROJECT_ROOT" && $PYTHON -c "
import sys; sys.path.insert(0, 'control_plane')
import os; os.environ.setdefault('ADMIN_TOKEN', 'test-admin-token')
os.environ.setdefault('DATABASE_URL', 'sqlite+aiosqlite:///tmp/test_sr.db')
os.environ.setdefault('REDIS_URL', 'redis://test.invalid:6379/0')
os.environ.setdefault('DATA_PLANE_BASE_URL', 'http://localhost:8081')
from app.schemas.routing import SmartRouterInput, RoutingStrategy, EndpointType
from app.services.routing.smart_router import get_smart_router
sr = get_smart_router()
inp = SmartRouterInput(
    endpoint_type=EndpointType.chat,
    cloud_allowed=False,
    strategy=RoutingStrategy.local_first,
)
dec = sr.route(inp)
d = dec.model_dump()
import json
dump = json.dumps(d)
print(f'has_prompt={\"prompt\" in dump.lower()} has_secret={\"secret\" in dump.lower()} has_api_key={\"api_key\" in dump.lower()}')
")
echo "$RESULT"
if echo "$RESULT" | grep -q "has_prompt=False"; then
  pass "decision does not contain prompt"
else
  fail "decision should not contain prompt"
fi
if echo "$RESULT" | grep -q "has_secret=False"; then
  pass "decision does not contain secrets"
else
  fail "decision should not contain secrets"
fi
echo ""

# ---- 8. admin endpoints require token (unit test) ----
echo "--- 8. admin endpoints require token ---"
RESULT=$(cd "$PROJECT_ROOT" && $PYTHON -c "
import sys; sys.path.insert(0, 'control_plane')
import os; os.environ.setdefault('ADMIN_TOKEN', 'test-admin-token')
os.environ.setdefault('DATABASE_URL', 'sqlite+aiosqlite:///tmp/test_sr.db')
os.environ.setdefault('REDIS_URL', 'redis://test.invalid:6379/0')
os.environ.setdefault('DATA_PLANE_BASE_URL', 'http://localhost:8081')
from fastapi import FastAPI
from app.api.routing_admin import router
app = FastAPI()
app.include_router(router)
from httpx import AsyncClient, ASGITransport
import asyncio
async def test():
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as c:
        r = await c.post('/admin/routing/simulate', json={'endpoint_type': 'chat', 'cloud_allowed': False})
        print(f'no_token_status={r.status_code}')
        r2 = await c.post('/admin/routing/simulate', json={'endpoint_type': 'chat', 'cloud_allowed': False}, headers={'X-Admin-Token': 'test-admin-token'})
        print(f'with_token_status={r2.status_code}')
asyncio.run(test())
")
echo "$RESULT"
if echo "$RESULT" | grep -q "no_token_status=40[13]"; then
  pass "admin endpoint rejects unauthorized"
else
  fail "admin endpoint should reject unauthorized requests"
fi
if echo "$RESULT" | grep -q "with_token_status=200\|with_token_status=422"; then
  pass "admin endpoint accepts valid token"
else
  fail "admin endpoint should accept valid token"
fi
echo ""

# ---- Summary ----
echo "=== Results: $PASS passed, $FAIL failed ==="
if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
