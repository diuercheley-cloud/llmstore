import pytest
from app.db.base import Base
from app.models.core.client import Client
from app.models.core.quota_counter import QuotaCounter
from app.services.quota import record_embedding_usage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest.mark.asyncio
async def test_record_embedding_usage(isolated_db_url):
    """
    Testa se o uso de embeddings é registrado corretamente nos contadores de cota.
    """
    engine = create_async_engine(isolated_db_url)
    session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_local() as db_session:
        client = Client(name="test-client", rate_limit_per_minute=10)
        db_session.add(client)
        await db_session.commit()
        await db_session.refresh(client)

        input_count = 5
        tokens = 100

        await record_embedding_usage(db_session, client.id, input_count, tokens)
        await db_session.commit()

        # Verificar contador mensal
        from datetime import date

        from app.services.quota import month_start

        res = await db_session.execute(
            select(QuotaCounter).where(
                QuotaCounter.client_id == client.id,
                QuotaCounter.period_type == "monthly",
                QuotaCounter.period_start == month_start(date.today()),
            )
        )
        counter = res.scalar_one()
        assert counter.used_embeddings_requests == 1
        assert counter.used_embeddings_tokens == tokens

    await engine.dispose()
