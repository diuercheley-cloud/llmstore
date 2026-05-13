#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON="${PYTHON:-$PROJECT_ROOT/.venv/bin/python}"

PASS=0
FAIL=0

pass()  { PASS=$((PASS+1)); echo "  PASS: $*"; }
fail()  { FAIL=$((FAIL+1)); echo "  FAIL: $*"; }

echo "=============================================="
echo "  Intelligent Cache Local Validation Suite"
echo "=============================================="
echo ""

echo "--- 1. Exact cache MISS then HIT ---"
RESULT=$($PYTHON -c "
import sys; sys.path.insert(0, '$PROJECT_ROOT/control_plane')
import os
os.environ.setdefault('ADMIN_TOKEN', 'test-admin-token')
os.environ.setdefault('DATABASE_URL', 'sqlite+aiosqlite:///tmp/test_cache_exact.db')
os.environ.setdefault('REDIS_URL', 'redis://test.invalid:6379/0')
os.environ.setdefault('DATA_PLANE_BASE_URL', 'http://localhost:8081')
os.environ.setdefault('RESPONSE_CACHE_ENABLED', 'true')
os.environ.setdefault('SEMANTIC_CACHE_ENABLED', 'false')

import asyncio, tempfile, json, uuid
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.db.base import Base
from app.services.cache.intelligent_cache import build_cache_key, get_exact, set_exact

async def test():
    db_path = os.path.join(tempfile.gettempdir(), f'test_cache_exact_{os.getpid()}.db')
    engine = create_async_engine(f'sqlite+aiosqlite:///{db_path}')
    session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    c1 = uuid.uuid4()
    async with session_local() as s:
        model = 'gemma'
        messages = [{'role': 'user', 'content': 'ola'}]
        temp = 0.7
        top_p = 0.95
        max_tokens = 128
        req_hash, prefix, fingerprint = build_cache_key(
            model=model, endpoint_type='chat', messages=messages,
            temperature=temp, top_p=top_p, max_tokens=max_tokens, client_id=str(c1),
        )

        # MISS
        miss = await get_exact(s, client_id=c1, endpoint_type='chat', model=model, request_hash=req_hash)
        assert not miss.hit, 'Expected MISS on first lookup'
        print(f'miss_hit={miss.hit} miss_type={miss.cache_type}')

        # SET
        await set_exact(s, client_id=c1, endpoint_type='chat', model=model,
                        provider='local', request_hash=req_hash,
                        request_fingerprint=fingerprint,
                        response_payload={'choices': [{'message': {'content': 'hello'}}]},
                        prompt_tokens=10, completion_tokens=5)
        await s.commit()

    async with session_local() as s:
        # HIT
        hit = await get_exact(s, client_id=c1, endpoint_type='chat', model=model, request_hash=req_hash)
        assert hit.hit, 'Expected HIT on second lookup'
        assert hit.cache_type == 'exact', 'Expected exact cache type'
        print(f'hit_hit={hit.hit} hit_type={hit.cache_type}')

    await engine.dispose()
    try: os.unlink(db_path)
    except: pass

asyncio.run(test())
")
echo "$RESULT"
if echo "$RESULT" | grep -q "hit_hit=True"; then
  pass "exact cache MISS then HIT"
else
  fail "exact cache MISS then HIT did not work"
fi
echo ""

echo "--- 2. Cache isolation per tenant (client_id) ---"
RESULT=$($PYTHON -c "
import sys; sys.path.insert(0, '$PROJECT_ROOT/control_plane')
import os
os.environ.setdefault('ADMIN_TOKEN', 'test-admin-token')
os.environ.setdefault('DATABASE_URL', 'sqlite+aiosqlite:///tmp/test_cache_isolation.db')
os.environ.setdefault('REDIS_URL', 'redis://test.invalid:6379/0')
os.environ.setdefault('DATA_PLANE_BASE_URL', 'http://localhost:8081')
os.environ.setdefault('RESPONSE_CACHE_ENABLED', 'true')
os.environ.setdefault('SEMANTIC_CACHE_ENABLED', 'false')

import asyncio, tempfile, uuid
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.db.base import Base
from app.services.cache.intelligent_cache import build_cache_key, get_exact, set_exact

async def test():
    db_path = os.path.join(tempfile.gettempdir(), f'test_cache_iso_{os.getpid()}.db')
    engine = create_async_engine(f'sqlite+aiosqlite:///{db_path}')
    session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    c1 = uuid.uuid4()
    c2 = uuid.uuid4()
    model = 'gemma'
    messages = [{'role': 'user', 'content': 'ola'}]
    req_hash, prefix, fingerprint = build_cache_key(
        model=model, endpoint_type='chat', messages=messages,
        temperature=0.7, top_p=0.95, max_tokens=128, client_id='c1',
    )

    async with session_local() as s:
        await set_exact(s, client_id=c1, endpoint_type='chat', model=model,
                        provider='local', request_hash=req_hash,
                        request_fingerprint=fingerprint,
                        response_payload={'choices': [{'message': {'content': 'hello'}}]},
                        prompt_tokens=10, completion_tokens=5)
        await s.commit()

    # client_id='c2' should NOT see c1's cache for same request hash
    async with session_local() as s:
        hit_c1 = await get_exact(s, client_id=c1, endpoint_type='chat', model=model, request_hash=req_hash)
        hit_c2 = await get_exact(s, client_id=c2, endpoint_type='chat', model=model, request_hash=req_hash)
        print(f'c1_hit={hit_c1.hit} c2_hit={hit_c2.hit}')

    await engine.dispose()
    try: os.unlink(db_path)
    except: pass

asyncio.run(test())
")
echo "$RESULT"
if echo "$RESULT" | grep -q "c1_hit=True.*c2_hit=False"; then
  pass "cache isolation per tenant works"
else
  fail "cache isolation per tenant failed"
fi
echo ""

echo "--- 3. no_cache bypass works ---"
RESULT=$($PYTHON -c "
import sys; sys.path.insert(0, '$PROJECT_ROOT/control_plane')
import os
os.environ.setdefault('ADMIN_TOKEN', 'test-admin-token')
os.environ.setdefault('DATABASE_URL', 'sqlite+aiosqlite:///tmp/test_cache_nocache.db')
os.environ.setdefault('REDIS_URL', 'redis://test.invalid:6379/0')
os.environ.setdefault('DATA_PLANE_BASE_URL', 'http://localhost:8081')
os.environ.setdefault('RESPONSE_CACHE_ENABLED', 'true')

import asyncio, tempfile, uuid
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.db.base import Base
from app.services.cache.intelligent_cache import should_cache

async def test():
    db_path = os.path.join(tempfile.gettempdir(), f'test_cache_nc_{os.getpid()}.db')
    engine = create_async_engine(f'sqlite+aiosqlite:///{db_path}')
    session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_local() as s:
        enabled, semantic, ttl = await should_cache(s, client_id=uuid.uuid4(), no_cache=True)
        print(f'cache_enabled={enabled} semantic_enabled={semantic} ttl={ttl}')

    await engine.dispose()
    try: os.unlink(db_path)
    except: pass

asyncio.run(test())
")
echo "$RESULT"
if echo "$RESULT" | grep -q "cache_enabled=False"; then
  pass "no_cache bypass works"
else
  fail "no_cache bypass did not work"
fi
echo ""

echo "--- 4. Semantic cache disabled by default ---"
RESULT=$($PYTHON -c "
import sys; sys.path.insert(0, '$PROJECT_ROOT/control_plane')
import os
os.environ.setdefault('ADMIN_TOKEN', 'test-admin-token')
os.environ.setdefault('DATABASE_URL', 'sqlite+aiosqlite:///tmp/test_cache_sem_default.db')
os.environ.setdefault('REDIS_URL', 'redis://test.invalid:6379/0')
os.environ.setdefault('DATA_PLANE_BASE_URL', 'http://localhost:8081')
os.environ.setdefault('RESPONSE_CACHE_ENABLED', 'true')
os.environ.setdefault('SEMANTIC_CACHE_ENABLED', 'false')

import asyncio, tempfile, uuid
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.db.base import Base
from app.services.cache.intelligent_cache import get_semantic

async def test():
    db_path = os.path.join(tempfile.gettempdir(), f'test_cache_sd_{os.getpid()}.db')
    engine = create_async_engine(f'sqlite+aiosqlite:///{db_path}')
    session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_local() as s:
        result = await get_semantic(s, client_id=uuid.uuid4(), endpoint_type='chat', model='gemma', normalized_prompt_hash='abc123')
        print(f'semantic_hit={result.hit} cache_type={result.cache_type}')

    await engine.dispose()
    try: os.unlink(db_path)
    except: pass

asyncio.run(test())
")
echo "$RESULT"
if echo "$RESULT" | grep -q "semantic_hit=False"; then
  pass "semantic cache disabled by default"
else
  fail "semantic cache should be disabled by default"
fi
echo ""

echo "--- 5. Semantic cache enabled in test mode with threshold ---"
RESULT=$($PYTHON -c "
import sys; sys.path.insert(0, '$PROJECT_ROOT/control_plane')
import os
os.environ.setdefault('ADMIN_TOKEN', 'test-admin-token')
os.environ.setdefault('DATABASE_URL', 'sqlite+aiosqlite:///tmp/test_cache_sem.db')
os.environ.setdefault('REDIS_URL', 'redis://test.invalid:6379/0')
os.environ.setdefault('DATA_PLANE_BASE_URL', 'http://localhost:8081')
os.environ.setdefault('RESPONSE_CACHE_ENABLED', 'true')
os.environ.setdefault('SEMANTIC_CACHE_ENABLED', 'true')

import asyncio, tempfile, uuid
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.db.base import Base
from app.services.cache.intelligent_cache import get_semantic, set_semantic

async def test():
    db_path = os.path.join(tempfile.gettempdir(), f'test_cache_sem_{os.getpid()}.db')
    engine = create_async_engine(f'sqlite+aiosqlite:///{db_path}')
    session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    c1 = uuid.uuid4()
    async with session_local() as s:
        # Set a semantic entry
        await set_semantic(s, client_id=c1, endpoint_type='chat', model='gemma',
                           provider='local', normalized_prompt_hash='abc123',
                           response_payload={'choices': [{'message': {'content': 'hello'}}]},
                           prompt_tokens=10, completion_tokens=5)
        await s.commit()

    async with session_local() as s:
        # Same hash - should hit (score=1.0 >= 0.85)
        hit = await get_semantic(s, client_id=c1, endpoint_type='chat', model='gemma',
                                 normalized_prompt_hash='abc123', threshold=0.85)
        # Different hash - should miss with threshold=0.99 (score < 0.99)
        miss = await get_semantic(s, client_id=c1, endpoint_type='chat', model='gemma',
                                  normalized_prompt_hash='different-prompt', threshold=0.99)
        print(f'hit_hit={hit.hit} miss_hit={miss.hit}')

    await engine.dispose()
    try: os.unlink(db_path)
    except: pass

asyncio.run(test())
")
echo "$RESULT"
if echo "$RESULT" | grep -q "hit_hit=True.*miss_hit=False"; then
  pass "semantic cache works with threshold"
else
  fail "semantic cache threshold test failed"
fi
echo ""

echo "--- 6. Usage records cache_hit ---"
RESULT=$($PYTHON -c "
import sys; sys.path.insert(0, '$PROJECT_ROOT/control_plane')
import os
os.environ.setdefault('ADMIN_TOKEN', 'test-admin-token')
os.environ.setdefault('DATABASE_URL', 'sqlite+aiosqlite:///tmp/test_cache_usage.db')
os.environ.setdefault('REDIS_URL', 'redis://test.invalid:6379/0')
os.environ.setdefault('DATA_PLANE_BASE_URL', 'http://localhost:8081')

import asyncio, tempfile, json
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.db.base import Base
from app.models.request_log import RequestLog
from app.core.time import utc_now

async def test():
    db_path = os.path.join(tempfile.gettempdir(), f'test_cache_usage_{os.getpid()}.db')
    engine = create_async_engine(f'sqlite+aiosqlite:///{db_path}')
    session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    import uuid
    now = utc_now()
    cid = uuid.uuid4()
    async with session_local() as s:
        entry = RequestLog(
            client_id=cid,
            model='gemma',
            endpoint='chat',
            prompt_tokens_estimated=10,
            completion_tokens_estimated=5,
            cache_hit=True,
            latency_ms=100,
            http_status=200,
            backend_name='local',
            is_stream=False,
            estimated_cost_usd=0.0,
            attempts=1,
            fallback_used=False,
            created_at=now,
        )
        s.add(entry)
        await s.commit()

    async with session_local() as s:
        from sqlalchemy import select
        row = (await s.execute(select(RequestLog).where(RequestLog.client_id == cid))).scalar_one()
        print(f'cache_hit={row.cache_hit}')

    await engine.dispose()
    try: os.unlink(db_path)
    except: pass

asyncio.run(test())
")
echo "$RESULT"
if echo "$RESULT" | grep -q "cache_hit=True"; then
  pass "usage records cache_hit"
else
  fail "usage should record cache_hit"
fi
echo ""

echo "--- 7. Billing reduces cost on hit ---"
RESULT=$($PYTHON -c "
import sys; sys.path.insert(0, '$PROJECT_ROOT/control_plane')
import os
os.environ.setdefault('ADMIN_TOKEN', 'test-admin-token')
os.environ.setdefault('DATABASE_URL', 'sqlite+aiosqlite:///tmp/test_cache_billing.db')
os.environ.setdefault('REDIS_URL', 'redis://test.invalid:6379/0')
os.environ.setdefault('DATA_PLANE_BASE_URL', 'http://localhost:8081')

from app.services.billing.pricing_engine import calculate_customer_price
r_nc = calculate_customer_price(plan_code='basic', prompt_tokens=100, completion_tokens=50, cache_hit=False)
r_ch = calculate_customer_price(plan_code='basic', prompt_tokens=100, completion_tokens=50, cache_hit=True)
print(f'no_cache={r_nc.price_brl} cache_hit={r_ch.price_brl}')
")
echo "$RESULT"
if echo "$RESULT" | python3 -c "
import sys
line = sys.stdin.read().strip()
print(line)
no_cache = float(line.split()[0].split('=')[1])
cache_hit = float(line.split()[1].split('=')[1])
if cache_hit <= no_cache:
    sys.exit(0)
else:
    sys.exit(1)
"; then
  pass "billing reduces cost on hit"
else
  fail "billing should reduce cost on cache hit"
fi
echo ""

echo "--- 8. Admin stats don't leak prompts ---"
RESULT=$($PYTHON -c "
import sys; sys.path.insert(0, '$PROJECT_ROOT/control_plane')
import os
os.environ.setdefault('ADMIN_TOKEN', 'test-admin-token')
os.environ.setdefault('DATABASE_URL', 'sqlite+aiosqlite:///tmp/test_cache_admin.db')
os.environ.setdefault('REDIS_URL', 'redis://test.invalid:6379/0')
os.environ.setdefault('DATA_PLANE_BASE_URL', 'http://localhost:8081')
os.environ.setdefault('RESPONSE_CACHE_ENABLED', 'true')
os.environ.setdefault('SEMANTIC_CACHE_ENABLED', 'false')

import asyncio, tempfile, uuid
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.db.base import Base
from app.services.cache.intelligent_cache import set_exact, list_cache_entries, build_cache_key

async def test():
    db_path = os.path.join(tempfile.gettempdir(), f'test_cache_admin_{os.getpid()}.db')
    engine = create_async_engine(f'sqlite+aiosqlite:///{db_path}')
    session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    c1 = uuid.uuid4()
    async with session_local() as s:
        req_hash, prefix, fingerprint = build_cache_key(
            model='gemma', endpoint_type='chat',
            messages=[{'role': 'user', 'content': 'my secret prompt with password=123'}],
            temperature=0.7, top_p=0.95, max_tokens=128, client_id=str(c1),
        )
        await set_exact(s, client_id=c1, endpoint_type='chat', model='gemma',
                        provider='local', request_hash=req_hash,
                        request_fingerprint=fingerprint,
                        normalized_prompt_hash='abc123',
                        response_payload={'choices': [{'message': {'content': 'ok'}}]},
                        prompt_tokens=5, completion_tokens=2)
        await s.commit()

    async with session_local() as s:
        entries = await list_cache_entries(s)
        raw = str(entries)
        leak_prompt = 'my secret prompt' in raw
        # Check hashes are truncated
        request_hash_truncated = '...' in str([e['request_hash'] for e in entries])
        print(f'leak_prompt={leak_prompt} truncated={request_hash_truncated}')

    await engine.dispose()
    try: os.unlink(db_path)
    except: pass

asyncio.run(test())
")
echo "$RESULT"
if echo "$RESULT" | grep -q "leak_prompt=False.*truncated=True"; then
  pass "admin stats don't leak prompts"
else
  fail "admin stats should not leak prompts"
fi
echo ""

echo "=============================================="
echo "  Results: $PASS passed, $FAIL failed"
echo "=============================================="
if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
