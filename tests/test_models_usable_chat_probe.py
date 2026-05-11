import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.db.base import Base
from app.models.model_registry import ModelRegistry
from app.services.model_policy import get_usable_chat_model

@pytest_asyncio.fixture
async def session(isolated_db_url):
    engine = create_async_engine(isolated_db_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async with session_factory() as session:
        yield session
        
    await engine.dispose()

@pytest.mark.asyncio
async def test_get_usable_chat_model_finds_default(session: AsyncSession):
    """Verifica se encontra o modelo padrão se ele for chat e ready."""
    # Criar modelo padrão
    new_model = ModelRegistry(
        model_id="default-chat-model",
        provider="llama.cpp",
        model_file="test.gguf",
        is_active=True,
        is_default=True,
        context_length=2048
    )
    session.add(new_model)
    await session.commit()
    
    # Em ambiente de teste, local_ready deve ser True por causa do fallback mock
    model_card, error = await get_usable_chat_model(session)
    assert error is None
    assert model_card is not None
    assert model_card["id"] == "default-chat-model"
    assert model_card["capabilities"]["chat"] is True
    assert model_card["local_ready"] is True

@pytest.mark.asyncio
async def test_get_usable_chat_model_skips_embeddings(session: AsyncSession):
    """Verifica se ignora modelos que são apenas embedding."""
    new_model = ModelRegistry(
        model_id="my-embedding-model",
        provider="openai_compatible",
        model_file="none",
        is_active=True,
        is_default=True,
        metadata_json='{"type": "embedding"}',
        context_length=2048
    )
    session.add(new_model)
    await session.commit()
    
    model_card, error = await get_usable_chat_model(session)
    # Não deve encontrar modelo de chat
    assert model_card is None
    assert error == "no_chat_models_registered"

@pytest.mark.asyncio
async def test_get_usable_chat_model_no_models(session: AsyncSession):
    """Verifica comportamento quando não há modelos registrados."""
    model_card, error = await get_usable_chat_model(session)
    assert model_card is None
    assert error == "no_models_registered"
