import json
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from app.db.base import Base
from app.models.core.semantic_cache_entry import SemanticCacheEntry
from app.services.cache.intelligent_cache import (
    _compute_semantic_embedding_id,
    _entry_to_embedding_vector,
    get_semantic,
    set_semantic,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest.mark.asyncio
async def test_semantic_cache_disabled_by_default(isolated_db_url):
    engine = create_async_engine(isolated_db_url)
    testing_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with testing_session() as session:
        result = await get_semantic(
            session,
            client_id=str(uuid.uuid4()),
            endpoint_type="chat",
            model="gemma",
            normalized_prompt_hash="abc123",
        )
        assert result.hit is False
        assert result.cache_type == "none"

    await engine.dispose()


@pytest.mark.asyncio
@patch("app.services.cache.intelligent_cache.settings.semantic_cache_enabled", True)
async def test_semantic_cache_hit(isolated_db_url):
    engine = create_async_engine(isolated_db_url)
    testing_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    client_id = uuid.uuid4()
    prompt_hash = "hit-test-prompt"

    async with testing_session() as session:
        await set_semantic(
            session,
            client_id=client_id,
            endpoint_type="chat",
            model="gemma",
            normalized_prompt_hash=prompt_hash,
            response_payload={"content": "hello world"},
            prompt_tokens=10,
            completion_tokens=20,
        )
        await session.commit()

    async with testing_session() as session:
        result = await get_semantic(
            session,
            client_id=client_id,
            endpoint_type="chat",
            model="gemma",
            normalized_prompt_hash=prompt_hash,
        )
        assert result.hit is True
        assert result.payload == {"content": "hello world"}
        assert result.cache_type == "semantic"

    await engine.dispose()


@pytest.mark.asyncio
@patch("app.services.cache.intelligent_cache.settings.semantic_cache_enabled", True)
async def test_semantic_cache_miss_below_threshold(isolated_db_url):
    engine = create_async_engine(isolated_db_url)
    testing_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    client_id = uuid.uuid4()
    now = datetime.now(UTC)

    different_hash = "different-hash"
    different_vector = _entry_to_embedding_vector(different_hash)
    low_vector = _entry_to_embedding_vector("low-score-original")

    async with testing_session() as session:
        entry = SemanticCacheEntry(
            client_id=client_id,
            endpoint_type="chat",
            model="gemma",
            normalized_prompt_hash="low-score-original",
            semantic_embedding_id=_compute_semantic_embedding_id("low-score-original"),
            response_json='{"content": "test"}',
            similarity_score=0.3,
            threshold_used=0.85,
            ttl_seconds=3600,
            expires_at=now + timedelta(hours=1),
            is_active=True,
            metadata_json=json.dumps(
                {"embedding_vector": low_vector, "embedding_dimensions": len(low_vector)}
            ),
            created_at=now,
            updated_at=now,
        )
        session.add(entry)
        await session.commit()

    async with testing_session() as session:
        result = await get_semantic(
            session,
            client_id=client_id,
            endpoint_type="chat",
            model="gemma",
            normalized_prompt_hash=different_hash,
        )
        assert result.hit is False
        assert result.similarity_score < 1.0

    await engine.dispose()


@pytest.mark.asyncio
@patch("app.services.cache.intelligent_cache.settings.semantic_cache_enabled", True)
async def test_semantic_cache_client_id_required(isolated_db_url):
    engine = create_async_engine(isolated_db_url)
    testing_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with testing_session() as session:
        with pytest.raises(TypeError):
            await get_semantic(
                session,
                endpoint_type="chat",
                model="gemma",
                normalized_prompt_hash="abc",
            )

    await engine.dispose()


def test_semantic_cache_embedding_deterministic():
    prompt_hash = "same-prompt"
    first = _compute_semantic_embedding_id(prompt_hash)
    second = _compute_semantic_embedding_id(prompt_hash)
    assert first == second

    third = _compute_semantic_embedding_id("different-prompt")
    assert first != third

    vec1 = _entry_to_embedding_vector("hello")
    vec2 = _entry_to_embedding_vector("hello")
    vec3 = _entry_to_embedding_vector("world")
    assert vec1 == vec2
    assert vec1 != vec3
