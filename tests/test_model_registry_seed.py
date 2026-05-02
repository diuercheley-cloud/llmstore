import json

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.core.config import get_settings
from app.db.base import Base
from app.models.inference_backend import InferenceBackend
from app.models.model_registry import ModelRegistry
from app.services.model_registry import ensure_default_model


@pytest.mark.asyncio
async def test_seed_keeps_bonsai_inactive_by_default(monkeypatch, isolated_db_url):
    monkeypatch.setenv("DATA_PLANE_BASE_URL", "http://data-plane-gemma:8081")
    monkeypatch.setenv("BONSAI_BASE_URL", "http://data-plane-bonsai:8082")
    monkeypatch.setenv("BONSAI_ENABLED", "false")
    monkeypatch.setenv("MODEL_ID", "unsloth/gemma-4-E4B-it-GGUF")
    monkeypatch.setenv("MODEL_FILE", "gemma-4-E4B-it-Q4_0.gguf")
    monkeypatch.setenv("BONSAI_MODEL_ID", "bonsai/bonsai-8B-GGUF")
    monkeypatch.setenv("BONSAI_MODEL_FILE", "bonsai-8B.gguf")
    get_settings.cache_clear()

    engine = create_async_engine(isolated_db_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with SessionLocal() as session:
        model = await ensure_default_model(session)
        await session.commit()

        assert model.model_alias == "gemma"
        backends = {
            item.name: item
            for item in (await session.execute(select(InferenceBackend))).scalars().all()
        }
        assert backends["gemma-local"].is_active is True
        assert backends["bonsai-local"].is_active is False

        models = {
            item.model_alias: item
            for item in (await session.execute(select(ModelRegistry))).scalars().all()
        }
        assert models["gemma"].is_active is True
        assert models["gemma"].is_default is True
        assert models["bonsai"].is_active is False
        assert models["bonsai"].status == "optional-disabled"
        assert models["bonsai"].prompt_template == "qwen"

    await engine.dispose()
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_seed_activates_bonsai_when_enabled(monkeypatch, isolated_db_url):
    monkeypatch.setenv("DATA_PLANE_BASE_URL", "http://data-plane-gemma:8081")
    monkeypatch.setenv("BONSAI_BASE_URL", "http://data-plane-bonsai:8082")
    monkeypatch.setenv("BONSAI_ENABLED", "true")
    monkeypatch.setenv("MODEL_ID", "unsloth/gemma-4-E4B-it-GGUF")
    monkeypatch.setenv("MODEL_FILE", "gemma-4-E4B-it-Q4_0.gguf")
    monkeypatch.setenv("BONSAI_MODEL_ID", "bonsai/bonsai-8B-GGUF")
    monkeypatch.setenv("BONSAI_MODEL_FILE", "bonsai-8B.gguf")
    get_settings.cache_clear()

    engine = create_async_engine(isolated_db_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with SessionLocal() as session:
        await ensure_default_model(session)
        await session.commit()

        backends = {
            item.name: item
            for item in (await session.execute(select(InferenceBackend))).scalars().all()
        }
        assert backends["bonsai-local"].is_active is True
        assert backends["bonsai-local"].backend_url == "http://data-plane-bonsai:8082"

        models = {
            item.model_alias: item
            for item in (await session.execute(select(ModelRegistry))).scalars().all()
        }
        assert models["bonsai"].is_active is True
        assert models["bonsai"].is_default is False
        assert models["bonsai"].prompt_template == "qwen"
        metadata = json.loads(models["bonsai"].metadata_json)
        assert metadata["backend_name"] == "bonsai-local"
        assert metadata["architecture"] == "qwen3"

    await engine.dispose()
    get_settings.cache_clear()
