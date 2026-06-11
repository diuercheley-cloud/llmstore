from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest.fixture(autouse=True)
def backup_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    repo_root = tmp_path / "repo"
    backup_root = tmp_path / "backups"
    repo_root.mkdir(parents=True, exist_ok=True)
    backup_root.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", "k" * 32)
    monkeypatch.setenv("BACKUP_SIGNING_KEY", "s" * 32)
    monkeypatch.setenv("LLMSTACK_BACKUP_SOURCE_ROOT", str(repo_root))
    monkeypatch.setenv("BACKUP_RESTORE_ENABLED", "true")
    monkeypatch.setenv("DISASTER_RECOVERY_BACKUP_DIR", str(backup_root))

    yield {"repo_root": repo_root, "backup_root": backup_root}


@pytest.fixture
def backup_repo_root(backup_env) -> Path:
    return backup_env["repo_root"]


@pytest.fixture
def backup_store_root(backup_env) -> Path:
    return backup_env["backup_root"]


@pytest.fixture
def sqlite_backup_db_url(tmp_path: Path) -> str:
    return f"sqlite+aiosqlite:///{tmp_path / 'backup-dr.sqlite3'}"


@pytest_asyncio.fixture
async def sqlite_session_factory(sqlite_backup_db_url: str):
    import app.models  # noqa: F401
    from app.db.base import Base

    engine = create_async_engine(sqlite_backup_db_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield session_factory

    await engine.dispose()


def _postgres_test_url() -> str | None:
    return os.getenv("BACKUP_TEST_POSTGRES_URL") or os.getenv("DATABASE_URL")


def _looks_like_postgres(url: str | None) -> bool:
    return bool(url and (url.startswith("postgresql") or url.startswith("postgres")))


@pytest.fixture
def postgres_backup_db_url() -> str:
    url = _postgres_test_url()
    if not _looks_like_postgres(url):
        pytest.skip("BACKUP_TEST_POSTGRES_URL is not configured")
    if not shutil.which("pg_dump") or not shutil.which("pg_restore"):
        pytest.skip("pg_dump/pg_restore are required for PostgreSQL backup tests")
    return url


@pytest_asyncio.fixture
async def postgres_session_factory(postgres_backup_db_url: str):
    import app.models  # noqa: F401
    from app.db.base import Base

    engine = create_async_engine(postgres_backup_db_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield session_factory

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
