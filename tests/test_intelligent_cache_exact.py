import time

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.db.base import Base
from app.services.cache.intelligent_cache import (
    build_cache_key,
    get_exact,
    set_exact,
    normalize_request,
)


@pytest.mark.asyncio
async def test_exact_cache_miss_then_hit(isolated_db_url: str):
    engine = create_async_engine(isolated_db_url)
    testing_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with testing_session() as session:
        request_hash, prefix, fingerprint = build_cache_key(
            model="gemma",
            endpoint_type="/v1/chat/completions",
            messages=[{"role": "user", "content": "hello"}],
            temperature=0.7,
            top_p=0.95,
            max_tokens=512,
        )

        # MISS
        result = await get_exact(
            session, endpoint_type="/v1/chat/completions", model="gemma",
            request_hash=request_hash,
        )
        assert not result.hit
        assert result.cache_type == "none"

        # Store
        await set_exact(
            session, endpoint_type="/v1/chat/completions", model="gemma",
            request_hash=request_hash, request_fingerprint=fingerprint,
            response_payload={"choices": [{"message": {"content": "hi"}}]},
            prompt_tokens=10, completion_tokens=5,
        )
        await session.commit()

        # HIT
        result = await get_exact(
            session, endpoint_type="/v1/chat/completions", model="gemma",
            request_hash=request_hash,
        )
        assert result.hit
        assert result.cache_type == "exact"
        assert result.payload is not None

    await engine.dispose()


@pytest.mark.asyncio
async def test_exact_cache_different_requests_different_keys(isolated_db_url: str):
    engine = create_async_engine(isolated_db_url)
    testing_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with testing_session() as session:
        hash_a, _, fp_a = build_cache_key(
            model="gemma",
            endpoint_type="/v1/chat/completions",
            messages=[{"role": "user", "content": "hello"}],
            temperature=0.7, top_p=0.95, max_tokens=512,
        )
        hash_b, _, fp_b = build_cache_key(
            model="gemma",
            endpoint_type="/v1/chat/completions",
            messages=[{"role": "user", "content": "goodbye"}],
            temperature=0.7, top_p=0.95, max_tokens=512,
        )

        assert hash_a != hash_b
        assert fp_a != fp_b

        await set_exact(
            session, endpoint_type="/v1/chat/completions", model="gemma",
            request_hash=hash_a, request_fingerprint=fp_a,
            response_payload={"choices": [{"message": {"content": "hi"}}]},
            prompt_tokens=5, completion_tokens=3,
        )
        await session.commit()

        result_a = await get_exact(
            session, endpoint_type="/v1/chat/completions", model="gemma",
            request_hash=hash_a,
        )
        assert result_a.hit

        result_b = await get_exact(
            session, endpoint_type="/v1/chat/completions", model="gemma",
            request_hash=hash_b,
        )
        assert not result_b.hit

    await engine.dispose()


@pytest.mark.asyncio
async def test_exact_cache_ttl_expiry(isolated_db_url: str):
    engine = create_async_engine(isolated_db_url)
    testing_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with testing_session() as session:
        request_hash, prefix, fingerprint = build_cache_key(
            model="gemma",
            endpoint_type="/v1/chat/completions",
            messages=[{"role": "user", "content": "hello"}],
            temperature=0.7, top_p=0.95, max_tokens=512,
        )

        await set_exact(
            session, endpoint_type="/v1/chat/completions", model="gemma",
            request_hash=request_hash, request_fingerprint=fingerprint,
            response_payload={"choices": [{"message": {"content": "hi"}}]},
            prompt_tokens=5, completion_tokens=3,
            ttl_seconds=1,
        )
        await session.commit()

        result = await get_exact(
            session, endpoint_type="/v1/chat/completions", model="gemma",
            request_hash=request_hash,
        )
        assert result.hit

        time.sleep(1.1)

        result = await get_exact(
            session, endpoint_type="/v1/chat/completions", model="gemma",
            request_hash=request_hash,
        )
        assert not result.hit

    await engine.dispose()


@pytest.mark.asyncio
async def test_exact_cache_passthrough_when_disabled(isolated_db_url: str, monkeypatch: pytest.MonkeyPatch):
    import app.services.cache.intelligent_cache as cache_module

    engine = create_async_engine(isolated_db_url)
    testing_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with testing_session() as session:
        request_hash, prefix, fingerprint = build_cache_key(
            model="gemma",
            endpoint_type="/v1/chat/completions",
            messages=[{"role": "user", "content": "hello"}],
            temperature=0.7, top_p=0.95, max_tokens=512,
        )

        monkeypatch.setattr(cache_module.settings, "response_cache_enabled", False)

        await set_exact(
            session, endpoint_type="/v1/chat/completions", model="gemma",
            request_hash=request_hash, request_fingerprint=fingerprint,
            response_payload={"choices": [{"message": {"content": "hi"}}]},
            prompt_tokens=5, completion_tokens=3,
        )
        await session.commit()

        result = await get_exact(
            session, endpoint_type="/v1/chat/completions", model="gemma",
            request_hash=request_hash,
        )
        assert not result.hit
        assert result.cache_type == "none"

    await engine.dispose()


def test_build_cache_key_stability():
    result1 = build_cache_key(
        model="gemma",
        endpoint_type="/v1/chat/completions",
        messages=[{"role": "user", "content": "hello"}],
        temperature=0.7,
        top_p=0.95,
        max_tokens=512,
    )
    result2 = build_cache_key(
        model="gemma",
        endpoint_type="/v1/chat/completions",
        messages=[{"role": "user", "content": "hello"}],
        temperature=0.7,
        top_p=0.95,
        max_tokens=512,
    )
    assert result1 == result2


def test_normalize_request_stability():
    n1 = normalize_request(
        messages=[{"role": "user", "content": "hello"}],
        temperature=0.7,
        top_p=0.95,
        max_tokens=512,
        model="gemma",
    )
    n2 = normalize_request(
        messages=[{"role": "user", "content": "hello"}],
        temperature=0.7,
        top_p=0.95,
        max_tokens=512,
        model="gemma",
    )
    assert n1 == n2
