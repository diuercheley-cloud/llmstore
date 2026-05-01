import os
import sys
from collections import defaultdict
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI

# Resolve project root and load .env before any app imports
ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"
TEST_TMP = Path("/tmp/llm-inference-stack-tests")
TEST_TMP.mkdir(parents=True, exist_ok=True)
TEST_DB_FILE = TEST_TMP / "unit-tests.db"

if ENV_FILE.exists():
    with open(ENV_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key, value)

# Required fallbacks for tests
os.environ.setdefault("ADMIN_TOKEN", "test-admin-token")
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{TEST_DB_FILE}")
os.environ.setdefault("REDIS_URL", "redis://test.invalid:6379/0")
os.environ.setdefault("DATA_PLANE_BASE_URL", "http://localhost:8081")

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
        self._expires: dict[str, int] = {}
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def _record(self, name: str, *args: Any, **kwargs: Any) -> None:
        self.calls.append((name, args, kwargs))

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
            deleted += int(key in self._store)
            self._store.pop(key, None)
            self._lists.pop(key, None)
            self._expires.pop(key, None)
        return deleted

    async def incr(self, key: str) -> int:
        self._record("incr", key)
        value = int(self._store.get(key, 0)) + 1
        self._store[key] = value
        return value

    async def expire(self, key: str, seconds: int) -> bool:
        self._record("expire", key, seconds)
        if key not in self._store and key not in self._lists:
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
            "expires": dict(self._expires),
        }


@pytest.fixture
def fake_redis() -> FakeRedis:
    return FakeRedis()


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


@pytest_asyncio.fixture
async def app_client_factory() -> AsyncIterator[Callable[[FastAPI], Awaitable[httpx.AsyncClient]]]:
    clients: list[httpx.AsyncClient] = []

    async def _factory(app: FastAPI) -> httpx.AsyncClient:
        client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver")
        clients.append(client)
        return client

    yield _factory

    for client in clients:
        await client.aclose()
