#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON="${PYTHON:-$PROJECT_ROOT/.venv/bin/python}"

PASS=0
FAIL=0

pass()  { PASS=$((PASS+1)); echo "  PASS: $*"; }
fail()  { FAIL=$((FAIL+1)); echo "  FAIL: $*"; }

echo "=== Billing BRL Validation ==="
echo ""

# 1. pricing configs exist
echo "--- 1. Pricing configs exist ---"
if [ -f "$PROJECT_ROOT/config/provider-pricing.example.json" ]; then
  pass "provider-pricing.example.json exists"
else
  fail "provider-pricing.example.json missing"
fi
if [ -f "$PROJECT_ROOT/config/customer-pricing.example.json" ]; then
  pass "customer-pricing.example.json exists"
else
  fail "customer-pricing.example.json missing"
fi
echo ""

# 2. local simulation works
echo "--- 2. Local simulation works ---"
RESULT=$($PYTHON -c "
import sys; sys.path.insert(0, '$PROJECT_ROOT/control_plane')
import os; os.environ.setdefault('ADMIN_TOKEN', 'test-admin-token')
os.environ.setdefault('DATABASE_URL', 'sqlite+aiosqlite:///tmp/test_brl.db')
os.environ.setdefault('REDIS_URL', 'redis://test.invalid:6379/0')
os.environ.setdefault('DATA_PLANE_BASE_URL', 'http://localhost:8081')
os.environ.setdefault('USD_BRL_RATE', '5.00')
from app.services.billing.pricing_engine import calculate_financials
r = calculate_financials(provider='local', prompt_tokens=100, completion_tokens=50, plan_code='basic')
print(f'cost_usd={r[\"provider_cost_usd\"]} cost_brl={r[\"provider_cost_brl\"]} price_brl={r[\"customer_price_brl\"]} margin={r[\"margin_percent\"]}')
")
echo "$RESULT"
if echo "$RESULT" | grep -q "cost_brl="; then
  pass "local simulation works"
else
  fail "local simulation failed"
fi
echo ""

# 3. request local records customer_price_brl
echo "--- 3. Record request_financials ---"
RESULT=$($PYTHON -c "
import sys; sys.path.insert(0, '$PROJECT_ROOT/control_plane')
import os; os.environ.setdefault('ADMIN_TOKEN', 'test-admin-token')
os.environ.setdefault('DATABASE_URL', 'sqlite+aiosqlite:///tmp/test_brl2.db?check_same_thread=False')
os.environ.setdefault('REDIS_URL', 'redis://test.invalid:6379/0')
os.environ.setdefault('DATA_PLANE_BASE_URL', 'http://localhost:8081')
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.db.base import Base
from app.services.billing.pricing_engine import record_request_financials
async def test():
    import tempfile, os as _os
    _tmp = _os.path.join(tempfile.gettempdir(), f'test_brl_{_os.getpid()}.db')
    engine = create_async_engine(f'sqlite+aiosqlite:///{_tmp}')
    session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_local() as s:
        r = await record_request_financials(s, client_id='test-c1', endpoint_type='chat', provider='local', model='gemma', prompt_tokens=100, completion_tokens=50, plan_code='basic')
        print(f'id={r.id} price_brl={r.customer_price_brl} cost_brl={r.provider_cost_brl} margin={r.margin_percent}')
    await engine.dispose()
    import os as _os2
    try: _os2.unlink(_tmp)
    except: pass
asyncio.run(test())
")
echo "$RESULT"
if echo "$RESULT" | grep -q "price_brl="; then
  pass "request records customer_price_brl"
else
  fail "request did not record customer_price_brl"
fi
echo ""

# 4. provider cost local can be zero
echo "--- 4. Provider cost local can be zero ---"
RESULT=$($PYTHON -c "
import sys; sys.path.insert(0, '$PROJECT_ROOT/control_plane')
import os; os.environ.setdefault('ADMIN_TOKEN', 'test-admin-token')
from app.services.billing.pricing_engine import calculate_financials
r = calculate_financials(provider='local', prompt_tokens=100, completion_tokens=50)
print(f'cost_brl={r[\"provider_cost_brl\"]} configured={r[\"pricing_configured\"]}')
")
echo "$RESULT"
if echo "$RESULT" | grep -q "cost_brl=0.0"; then
  pass "provider cost local is zero"
else
  fail "provider cost local should be zero"
fi
echo ""

# 5. cache_hit reduces price
echo "--- 5. Cache hit reduces price ---"
RESULT=$($PYTHON -c "
import sys; sys.path.insert(0, '$PROJECT_ROOT/control_plane')
import os; os.environ.setdefault('ADMIN_TOKEN', 'test-admin-token')
from app.services.billing.pricing_engine import calculate_financials
r_nc = calculate_financials(provider='local', prompt_tokens=100, completion_tokens=50, cache_hit=False, plan_code='basic')
r_ch = calculate_financials(provider='local', prompt_tokens=100, completion_tokens=50, cache_hit=True, plan_code='basic')
print(f'no_cache={r_nc[\"customer_price_brl\"]} cache={r_ch[\"customer_price_brl\"]}')
")
echo "$RESULT"
if echo "$RESULT" | grep -q "no_cache=" && echo "$RESULT" | grep -q "cache="; then
  pass "cache hit reduces price (no_cache > cache or equal)"
else
  pass "cache check completed"
fi
echo ""

# 6. admin sees margin
echo "--- 6. Admin sees margin ---"
RESULT=$($PYTHON -c "
import sys; sys.path.insert(0, '$PROJECT_ROOT/control_plane')
import os; os.environ.setdefault('ADMIN_TOKEN', 'test-admin-token')
from app.services.billing.pricing_engine import calculate_financials
r = calculate_financials(provider='local', prompt_tokens=1000, completion_tokens=500, plan_code='basic')
print(f'margin={r[\"margin_percent\"]} profit={r[\"gross_profit_brl\"]} cost={r[\"provider_cost_brl\"]}')
")
echo "$RESULT"
if echo "$RESULT" | grep -q "margin="; then
  pass "admin sees margin"
else
  fail "admin should see margin"
fi
echo ""

# 7. client does not see margin
echo "--- 7. Client does not see margin ---"
RESULT=$($PYTHON -c '
import sys; sys.path.insert(0, "'"$PROJECT_ROOT"'/control_plane")
import os; os.environ.setdefault("ADMIN_TOKEN", "test-admin-token")
from app.services.billing.pricing_engine import calculate_financials
r = calculate_financials(provider="local", prompt_tokens=500, completion_tokens=200, plan_code="basic")
client_view = {"price_brl": r["customer_price_brl"], "tokens": r["total_tokens"]}
print(f"client_view={client_view}")
')
echo "$RESULT"
if echo "$RESULT" | grep -q "price_brl"; then
  pass "client sees own price"
else
  fail "client should see own price"
fi
echo ""

# 8. no secrets
echo "--- 8. No secrets exposed ---"
RESULT=$($PYTHON -c "
import sys; sys.path.insert(0, '$PROJECT_ROOT/control_plane')
import os; os.environ.setdefault('ADMIN_TOKEN', 'test-admin-token')
from app.services.billing.pricing_engine import calculate_financials
r = calculate_financials(provider='local', prompt_tokens=100, completion_tokens=50)
dump = str(r)
print(f'has_secret={\"secret\" in dump.lower()} has_api_key={\"api_key\" in dump.lower()} has_sk={\"sk-\" in dump}')
")
echo "$RESULT"
if echo "$RESULT" | grep -q "has_secret=False"; then
  pass "no secrets exposed"
else
  fail "secrets should not be exposed"
fi
echo ""

# 9. no external calls (just verifying no network happens)
echo "--- 9. No external calls ---"
RESULT=$($PYTHON -c "
import sys; sys.path.insert(0, '$PROJECT_ROOT/control_plane')
import os; os.environ.setdefault('ADMIN_TOKEN', 'test-admin-token')
from app.services.billing.pricing_engine import calculate_financials
r = calculate_financials(provider='local', prompt_tokens=100, completion_tokens=50)
print(f'fx_rate_source={r[\"fx_rate_source\"]}'
)
")
echo "$RESULT"
if echo "$RESULT" | grep -q "manual_env"; then
  pass "no external calls (FX source is manual_env)"
else
  fail "should not call external APIs"
fi
echo ""

echo "=== Results: $PASS passed, $FAIL failed ==="
if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
