import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.db.base import Base
from app.services.cache.intelligent_cache import (
    build_cache_key,
    ensure_cache_policy,
    list_cache_entries,
    set_exact,
    should_cache,
)


@pytest.mark.asyncio
async def test_no_cache_header_respected(isolated_db_url):
    engine = create_async_engine(isolated_db_url)
    testing_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with testing_session() as session:
        cache_enabled, semantic_enabled, ttl = await should_cache(
            session, no_cache=True,
        )
        assert cache_enabled is False
        assert semantic_enabled is False
        assert ttl == 0

    await engine.dispose()


@pytest.mark.asyncio
async def test_sensitive_prompt_not_cached(isolated_db_url):
    engine = create_async_engine(isolated_db_url)
    testing_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    client_id = uuid.uuid4()

    async with testing_session() as session:
        await ensure_cache_policy(
            session,
            client_id=client_id,
            cache_sensitive_data_allowed=False,
        )
        await session.commit()

    async with testing_session() as session:
        cache_enabled, semantic_enabled, ttl = await should_cache(
            session,
            client_id=client_id,
            sensitive_prompt=True,
        )
        assert cache_enabled is False

    await engine.dispose()


@pytest.mark.asyncio
async def test_cache_prompt_not_logged(isolated_db_url):
    engine = create_async_engine(isolated_db_url)
    testing_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    client_id = uuid.uuid4()
    request_hash, _, _ = build_cache_key(
        model="gemma", endpoint_type="chat",
        messages=[{"role": "user", "content": "my-secret-prompt"}],
        temperature=0.7, top_p=0.95, max_tokens=512,
    )

    async with testing_session() as session:
        await set_exact(
            session, client_id=client_id, endpoint_type="chat",
            model="gemma", request_hash=request_hash,
            request_fingerprint="fp",
            response_payload={"content": "response"},
        )
        await session.commit()

    async with testing_session() as session:
        entries = await list_cache_entries(session)
        for entry in entries:
            assert "response_json" not in entry
            assert entry.get("request_hash", "").endswith("...")

    await engine.dispose()


@pytest.mark.asyncio
async def test_cache_entry_no_prompt_content_in_admin(isolated_db_url):
    engine = create_async_engine(isolated_db_url)
    testing_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    client_id = uuid.uuid4()
    request_hash, _, _ = build_cache_key(
        model="gemma", endpoint_type="chat",
        messages=[{"role": "user", "content": "sensitive data"}],
        temperature=0.7, top_p=0.95, max_tokens=512,
    )

    async with testing_session() as session:
        await set_exact(
            session, client_id=client_id, endpoint_type="chat",
            model="gemma", request_hash=request_hash,
            request_fingerprint="fp",
            response_payload={"content": "secret response"},
        )
        await session.commit()

    async with testing_session() as session:
        entries = await list_cache_entries(session)
        assert len(entries) > 0
        for entry in entries:
            assert "prompt" not in entry.get("request_hash", "").lower()
            assert "response_json" not in entry

    await engine.dispose()
