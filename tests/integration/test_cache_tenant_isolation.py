import uuid

import pytest
from app.db.base import Base
from app.services.cache.intelligent_cache import (
    build_cache_key,
    get_exact,
    invalidate_client_cache,
    set_exact,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest.mark.asyncio
async def test_tenant_a_cannot_see_tenant_b_cache(isolated_db_url):
    engine = create_async_engine(isolated_db_url)
    testing_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    client_a = uuid.uuid4()
    client_b = uuid.uuid4()

    request_hash, _, _ = build_cache_key(
        model="gemma",
        endpoint_type="chat",
        messages=[{"role": "user", "content": "secret for a"}],
        temperature=0.7,
        top_p=0.95,
        max_tokens=512,
    )

    async with testing_session() as session:
        await set_exact(
            session,
            client_id=client_a,
            endpoint_type="chat",
            model="gemma",
            request_hash=request_hash,
            request_fingerprint="fp-a",
            response_payload={"content": "a-secret"},
        )
        await session.commit()

    async with testing_session() as session:
        result = await get_exact(
            session,
            client_id=client_b,
            endpoint_type="chat",
            model="gemma",
            request_hash=request_hash,
        )
        assert result.hit is False

    await engine.dispose()


@pytest.mark.asyncio
async def test_tenant_isolation_with_client_id_filter(isolated_db_url):
    engine = create_async_engine(isolated_db_url)
    testing_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    client_a = uuid.uuid4()
    client_b = uuid.uuid4()

    hash_a, _, _ = build_cache_key(
        model="gemma",
        endpoint_type="chat",
        messages=[{"role": "user", "content": "hello a"}],
        temperature=0.7,
        top_p=0.95,
        max_tokens=512,
    )
    hash_b, _, _ = build_cache_key(
        model="gemma",
        endpoint_type="chat",
        messages=[{"role": "user", "content": "hello b"}],
        temperature=0.7,
        top_p=0.95,
        max_tokens=512,
    )

    async with testing_session() as session:
        await set_exact(
            session,
            client_id=client_a,
            endpoint_type="chat",
            model="gemma",
            request_hash=hash_a,
            request_fingerprint="fp-a",
            response_payload={"content": "from a"},
        )
        await set_exact(
            session,
            client_id=client_b,
            endpoint_type="chat",
            model="gemma",
            request_hash=hash_b,
            request_fingerprint="fp-b",
            response_payload={"content": "from b"},
        )
        await session.commit()

    async with testing_session() as session:
        result_a = await get_exact(
            session,
            client_id=client_a,
            endpoint_type="chat",
            model="gemma",
            request_hash=hash_a,
        )
        result_b = await get_exact(
            session,
            client_id=client_b,
            endpoint_type="chat",
            model="gemma",
            request_hash=hash_b,
        )
        result_a_from_b = await get_exact(
            session,
            client_id=client_a,
            endpoint_type="chat",
            model="gemma",
            request_hash=hash_b,
        )
        assert result_a.hit is True
        assert result_b.hit is True
        assert result_a_from_b.hit is False

    await engine.dispose()


@pytest.mark.asyncio
async def test_cache_invalidate_by_client(isolated_db_url):
    engine = create_async_engine(isolated_db_url)
    testing_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    client_a = uuid.uuid4()
    client_b = uuid.uuid4()

    hash_a, _, _ = build_cache_key(
        model="gemma",
        endpoint_type="chat",
        messages=[{"role": "user", "content": "shared request"}],
        temperature=0.7,
        top_p=0.95,
        max_tokens=512,
    )

    async with testing_session() as session:
        await set_exact(
            session,
            client_id=client_a,
            endpoint_type="chat",
            model="gemma",
            request_hash=hash_a,
            request_fingerprint="fp-a",
            response_payload={"content": "a-data"},
        )
        await set_exact(
            session,
            client_id=client_b,
            endpoint_type="chat",
            model="gemma",
            request_hash=hash_a,
            request_fingerprint="fp-b",
            response_payload={"content": "b-data"},
        )
        await session.commit()

    async with testing_session() as session:
        await invalidate_client_cache(session, client_id=client_a)
        await session.commit()

    async with testing_session() as session:
        result_a = await get_exact(
            session,
            client_id=client_a,
            endpoint_type="chat",
            model="gemma",
            request_hash=hash_a,
        )
        result_b = await get_exact(
            session,
            client_id=client_b,
            endpoint_type="chat",
            model="gemma",
            request_hash=hash_a,
        )
        assert result_a.hit is False
        assert result_b.hit is True

    await engine.dispose()
