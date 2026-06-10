from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from app.db.base import Base
from app.services.inference import transparency_gossip
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def session(isolated_db_url):
    engine = create_async_engine(isolated_db_url)
    session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_local() as s:
        yield s
    await engine.dispose()

@pytest.mark.asyncio
async def test_checkpoint_consistency_match(session: AsyncSession):
    start = datetime.now(timezone.utc) - timedelta(hours=5)
    end = datetime.now(timezone.utc)
    
    cp1 = await transparency_gossip.create_consistency_checkpoint(session, "merkle_timeline", start, end)
    cp2 = await transparency_gossip.create_consistency_checkpoint(session, "merkle_timeline", start, end)
    
    # Since they have same start/end and no timelines exist in DB during test, they should have same root_hash (placeholder)
    # or at least we test the comparison function
    comparison = await transparency_gossip.compare_checkpoints(session, cp1.id, cp2.id)
    assert comparison["is_consistent"] is True
    assert comparison["period_match"] is True
