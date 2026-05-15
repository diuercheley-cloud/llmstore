import pytest
import uuid
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.inference import transparency_gossip
from app.models.commercial_transparency import CommercialConsistencyCheckpoint

import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.db.base import Base

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
async def test_create_checkpoint(session: AsyncSession):
    start = datetime.utcnow() - timedelta(days=1)
    end = datetime.utcnow()
    checkpoint = await transparency_gossip.create_consistency_checkpoint(
        session,
        "merkle_timeline",
        start,
        end
    )
    assert checkpoint.root_hash is not None
    assert checkpoint.checkpoint_type == "merkle_timeline"

@pytest.mark.asyncio
async def test_checkpoint_ingest_and_export(session: AsyncSession):
    payload = {
        "checkpoint_type": "receipt_chain",
        "period_start": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
        "period_end": datetime.utcnow().isoformat(),
        "root_hash": "a" * 64,
        "witness_summary": {"count": 5}
    }
    checkpoint = await transparency_gossip.ingest_checkpoint(session, payload)
    assert checkpoint.root_hash == "a" * 64
    
    exported = await transparency_gossip.export_checkpoint(checkpoint)
    assert exported["root_hash"] == "a" * 64
    assert exported["checkpoint_type"] == "receipt_chain"

@pytest.mark.asyncio
async def test_split_view_detection(session: AsyncSession):
    start = datetime.utcnow() - timedelta(hours=1)
    end = datetime.utcnow()
    
    # 1. Create first checkpoint
    cp1 = CommercialConsistencyCheckpoint(
        checkpoint_type="merkle_timeline",
        period_start=start,
        period_end=end,
        root_hash="hash_a"
    )
    session.add(cp1)
    await session.commit()
    
    # 2. Ingest conflicting checkpoint
    payload = {
        "checkpoint_type": "merkle_timeline",
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "root_hash": "hash_b"
    }
    cp2 = await transparency_gossip.ingest_checkpoint(session, payload)
    
    # 3. Verify alert was created
    from app.models.commercial_transparency import CommercialTransparencySplitViewAlert
    from sqlalchemy.future import select
    result = await session.execute(select(CommercialTransparencySplitViewAlert))
    alert = result.scalar_one_or_none()
    
    assert alert is not None
    assert alert.alert_type == "checkpoint_conflict"
    assert alert.expected_hash == "hash_a"
    assert alert.observed_hash == "hash_b"

@pytest.mark.asyncio
async def test_gossip_dry_run(session: AsyncSession):
    payload = {
        "peer_id": "cluster-east-1",
        "checkpoint_hash": "some_hash",
        "gossip_type": "push"
    }
    record = await transparency_gossip.gossip_with_peer(session, "cluster-east-1", payload)
    assert record.source_peer_id == "cluster-east-1"
    assert record.verification_status == "unknown" # No local checkpoint matches
