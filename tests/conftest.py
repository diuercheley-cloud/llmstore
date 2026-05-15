import os
import sys
from collections import defaultdict
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any, Optional
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

# Resolve project root and load .env before any app imports
ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"
ENV_LOCAL = ROOT / ".env.local"
TEST_TMP = Path("/tmp/llm-inference-stack-tests")
TEST_TMP.mkdir(parents=True, exist_ok=True)
TEST_DB_FILE = TEST_TMP / "unit-tests.db"

def _load_env_file(path: Path) -> None:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                os.environ.setdefault(key, value)

_load_env_file(ENV_FILE)
_load_env_file(ENV_LOCAL)

# Required fallbacks for tests
os.environ["ADMIN_TOKEN"] = "test-admin-token"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_FILE}?timeout=30"
os.environ["REDIS_URL"] = "redis://test.invalid:6379/0"
os.environ["DATA_PLANE_BASE_URL"] = "http://localhost:8081"
os.environ["RAG_STORAGE_DIR"] = str(TEST_TMP / "rag_uploads")
os.environ["LMSTUDIO_ENABLED"] = "false"
os.environ["TTS_ENABLED"] = "false"
os.environ["EMBEDDINGS_ENABLED"] = "true"
os.environ["EMBEDDINGS_BACKEND"] = "mock"

# Ensure control_plane is on path
CONTROL_PLANE = ROOT / "control_plane"
if CONTROL_PLANE.exists() and str(CONTROL_PLANE) not in sys.path:
    sys.path.insert(0, str(CONTROL_PLANE))

# Ensure app root is on path for imports like `from app import ...`
APP_ROOT = ROOT / "app"
if APP_ROOT.exists() and str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class FakeRedis:
    def __init__(self) -> None:
        self._store: dict[str, Any] = {}
        self._lists: dict[str, list[Any]] = defaultdict(list)
        self._zsets: dict[str, dict[str, float]] = defaultdict(dict)
        self._expires: dict[str, int] = {}
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []
        self._pipeline_ops: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []
        self._in_pipeline = False

    def _record(self, name: str, *args: Any, **kwargs: Any) -> None:
        self.calls.append((name, args, kwargs))

    def pipeline(self):
        self._in_pipeline = True
        self._pipeline_ops = []
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._in_pipeline = False

    async def execute(self):
        results = []
        for name, args, kwargs in self._pipeline_ops:
            method = getattr(self, f"_do_{name}", None)
            if method:
                res = await method(*args, **kwargs)
                results.append(res)
            else:
                results.append(None)
        self._pipeline_ops = []
        self._in_pipeline = False
        return results

    def __getattribute__(self, name):
        pipeline_methods = {"zremrangebyscore", "zcard", "zadd", "expire", "zcount"}
        try:
            in_pipeline = object.__getattribute__(self, "_in_pipeline")
        except AttributeError:
            in_pipeline = False

        if in_pipeline and name in pipeline_methods:
            def mock_method(*args, **kwargs):
                self._record(name, *args, **kwargs)
                self._pipeline_ops.append((name, args, kwargs))
                return self
            return mock_method
        return object.__getattribute__(self, name)

    async def _do_zremrangebyscore(self, key, min_val, max_val):
        count = 0
        to_del = []
        for member, score in self._zsets[key].items():
            if score >= min_val and score <= max_val:
                to_del.append(member)
        for m in to_del:
            del self._zsets[key][m]
            count += 1
        return count

    async def _do_zcard(self, key):
        return len(self._zsets[key])

    async def _do_zadd(self, key, mapping, **kwargs):
        for member, score in mapping.items():
            self._zsets[key][member] = float(score)
        return len(mapping)

    async def _do_expire(self, key, seconds):
        self._expires[key] = seconds
        return True

    async def _do_zcount(self, key, min_val, max_val):
        count = 0
        for score in self._zsets[key].values():
            if score >= min_val and score <= max_val:
                count += 1
        return count

    async def zadd(self, key, mapping, **kwargs):
        self._record("zadd", key, mapping)
        return await self._do_zadd(key, mapping)

    async def zcard(self, key):
        self._record("zcard", key)
        return await self._do_zcard(key)

    async def zpopmin(self, key, count=1):
        self._record("zpopmin", key, count)
        if not self._zsets[key]:
            return []
        sorted_items = sorted(self._zsets[key].items(), key=lambda x: x[1])
        result = []
        for i in range(min(count, len(sorted_items))):
            member, score = sorted_items[i]
            del self._zsets[key][member]
            result.append((member, score))
        return result

    async def zrange(self, key, start, stop, withscores=False):
        self._record("zrange", key, start, stop, withscores=withscores)
        if not self._zsets[key]:
            return []
        sorted_items = sorted(self._zsets[key].items(), key=lambda x: x[1])
        if stop == -1:
            stop = len(sorted_items) - 1
        subset = sorted_items[start:stop+1]
        if withscores:
            return subset
        return [item[0] for item in subset]

    async def zscore(self, key, member):
        self._record("zscore", key, member)
        return self._zsets[key].get(member)

    async def zremrangebyscore(self, key, min_val, max_val):
        self._record("zremrangebyscore", key, min_val, max_val)
        return await self._do_zremrangebyscore(key, min_val, max_val)

    async def eval(self, script, numkeys, *keys_and_args):
        self._record("eval", script, numkeys, *keys_and_args)
        if "redis.call('ZADD', queue_key, score - aging_step, job_id)" in script:
            queue_key = keys_and_args[0]
            aging_step = float(keys_and_args[1])
            for job_id in list(self._zsets[queue_key].keys()):
                self._zsets[queue_key][job_id] -= aging_step
            return len(self._zsets[queue_key])
        return None

    async def ping(self) -> bool:
        self._record("ping")
        return True

    async def aclose(self) -> None:
        self._record("aclose")

    async def get(self, key: str) -> Any:
        self._record("get", key)
        return self._store.get(key)

    async def set(self, key: str, value: Any, ex: int | None = None, nx: bool = False) -> bool:
        self._record("set", key, value, ex=ex, nx=nx)
        if nx and key in self._store:
            return False
        self._store[key] = value
        if ex is not None:
            self._expires[key] = ex
        return True

    async def delete(self, *keys: str) -> int:
        self._record("delete", *keys)
        deleted = 0
        for key in keys:
            if key in self._store:
                deleted += 1
                del self._store[key]
            if key in self._lists:
                deleted += 1
                del self._lists[key]
            if key in self._zsets:
                deleted += 1
                del self._zsets[key]
            self._expires.pop(key, None)
        return deleted

    async def incr(self, key: str) -> int:
        self._record("incr", key)
        value = int(self._store.get(key, 0)) + 1
        self._store[key] = value
        return value

    async def expire(self, key: str, seconds: int) -> bool:
        self._record("expire", key, seconds)
        if key not in self._store and key not in self._lists and key not in self._zsets:
            return False
        self._expires[key] = seconds
        return True

    async def ttl(self, key: str) -> int:
        self._record("ttl", key)
        return self._expires.get(key, -1)

    async def rpush(self, key: str, *values: Any) -> int:
        self._record("rpush", key, *values)
        self._lists[key].extend(values)
        return len(self._lists[key])

    async def llen(self, key: str) -> int:
        self._record("llen", key)
        return len(self._lists[key])

    async def lpop(self, key: str) -> Any:
        self._record("lpop", key)
        if not self._lists[key]:
            return None
        return self._lists[key].pop(0)

    async def blpop(self, key: str, timeout: int = 0) -> tuple[str, Any] | None:
        self._record("blpop", key, timeout)
        value = await self.lpop(key)
        if value is None:
            return None
        return key, value

    def snapshot(self) -> dict[str, Any]:
        return {
            "store": dict(self._store),
            "lists": {key: list(values) for key, values in self._lists.items()},
            "zsets": {key: dict(values) for key, values in self._zsets.items()},
            "expires": dict(self._expires),
        }


@pytest.fixture
def fake_redis() -> FakeRedis:
    return FakeRedis()


@pytest.fixture
def redis_client(fake_redis) -> FakeRedis:
    return fake_redis


@pytest.fixture
def settings():
    from app.core.config import get_settings
    return get_settings()


@pytest.fixture(autouse=True)
def global_reset(monkeypatch: pytest.MonkeyPatch):
    """
    Resets global state between tests to ensure determinism.
    Autouse=True means it runs for EVERY test.
    """
    from app.core.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def isolated_db_url(tmp_path: Path) -> str:
    return f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"


@pytest_asyncio.fixture
async def fastapi_app() -> AsyncIterator[FastAPI]:
    app = FastAPI()
    yield app


@pytest_asyncio.fixture
async def async_client(fastapi_app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=fastapi_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.fixture
def app_client_factory():
    clients: list[httpx.AsyncClient] = []

    async def factory(app: FastAPI) -> httpx.AsyncClient:
        client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        )
        clients.append(client)
        return client

    return factory


@pytest.fixture
def admin_token_headers() -> dict[str, str]:
    return {"X-Admin-Token": os.environ.get("ADMIN_TOKEN", "test-admin-token")}


@pytest.fixture
def models_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from app.services import admin_model_management as model_mgmt
    directory = tmp_path / "models"
    directory.mkdir()
    monkeypatch.setattr(model_mgmt, "resolve_models_dir", lambda: directory)
    return directory


@pytest_asyncio.fixture
async def session(isolated_db_url) -> AsyncIterator[AsyncSession]:
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from app.db.base import Base

    engine = create_async_engine(isolated_db_url)
    testing_session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with testing_session_local() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def admin_client(isolated_db_url, fake_redis, models_dir) -> AsyncIterator[httpx.AsyncClient]:
    from app.main import app
    from app.db.session import get_db_session, get_redis
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from app.db.base import Base

    engine = create_async_engine(isolated_db_url)
    testing_session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db_session():
        async with testing_session_local() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_redis] = lambda: fake_redis

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()
    await engine.dispose()
