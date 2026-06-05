from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from app.db.base import Base
from app.models.commercial_transparency import (
    CommercialConsistencyCheckpoint,
)
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
async def test_detect_split_view_manual(session: AsyncSession):
    start = datetime.now(timezone.utc) - timedelta(days=2)
    end = datetime.now(timezone.utc) - timedelta(days=1)
    
    cp_local = CommercialConsistencyCheckpoint(
        checkpoint_type="merkle_timeline",
        period_start=start,
        period_end=end,
        root_hash="local_root"
    )
    session.add(cp_local)
    await session.commit()
    
    cp_remote = CommercialConsistencyCheckpoint(
        checkpoint_type="merkle_timeline",
        period_start=start,
        period_end=end,
        root_hash="remote_root"
    )
    session.add(cp_remote)
    await session.commit()
    
    alert = await transparency_gossip.detect_split_view(session, cp_remote)
    assert alert is not None
    assert alert.alert_type == "checkpoint_conflict"
    assert "remote_root" == alert.observed_hash
    assert "local_root" == alert.expected_hash
