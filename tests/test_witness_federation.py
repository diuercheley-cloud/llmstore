import uuid
from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from app.db.base import Base
from app.models.commercial_cryptographic_receipts import CommercialInferenceReceipt
from app.models.commercial_merkle_timelines import CommercialMerkleTimeline
from app.services.inference import witness_federation
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
async def test_witness_registration(session: AsyncSession):
    witness = await witness_federation.register_witness(
        session,
        name="Test Witness",
        witness_type="external",
        trust_level="high"
    )
    assert witness.witness_name == "Test Witness"
    assert witness.witness_type == "external"
    assert witness.status == "active"

@pytest.mark.asyncio
async def test_witness_signature_and_quorum(session: AsyncSession):
    # 1. Create a witness
    witness = await witness_federation.register_witness(
        session,
        name="Auditor A",
        witness_type="external"
    )
    
    # 2. Create a dummy timeline
    timeline = CommercialMerkleTimeline(
        timeline_type="inference_receipts",
        period_start=datetime.utcnow() - timedelta(hours=1),
        period_end=datetime.utcnow(),
        leaf_count=10,
        merkle_root="f" * 64,
        timeline_hash="timeline_hash_1",
        status="sealed"
    )
    session.add(timeline)
    await session.commit()
    await session.refresh(timeline)
    
    # 3. Request signature
    sig = await witness_federation.request_witness_signature(session, timeline.id, witness.id)
    assert sig is not None
    assert sig.verification_status == "valid"
    
    # 4. Evaluate quorum
    quorum = await witness_federation.evaluate_witness_quorum(session, timeline.id)
    assert quorum["quorum_status"] == "met"
    assert quorum["signatures_found"] == 1
    assert quorum["external_witness_present"] is True

@pytest.mark.asyncio
async def test_quorum_not_met(session: AsyncSession):
    # Create timeline without signatures
    timeline = CommercialMerkleTimeline(
        timeline_type="inference_receipts",
        period_start=datetime.utcnow() - timedelta(hours=1),
        period_end=datetime.utcnow(),
        leaf_count=5,
        merkle_root="e" * 64,
        timeline_hash="timeline_hash_2",
        status="sealed"
    )
    session.add(timeline)
    await session.commit()
    
    quorum = await witness_federation.evaluate_witness_quorum(session, timeline.id)
    # Default MIN_SIGNATURES is 1 in config (unless overridden by policy)
    assert quorum["quorum_status"] == "failed"

@pytest.mark.asyncio
async def test_proof_with_witness_data(session: AsyncSession):
    # Setup witness and signature
    witness = await witness_federation.register_witness(session, "Verifier B", "external")
    
    timeline = CommercialMerkleTimeline(
        timeline_type="inference_receipts",
        period_start=datetime.utcnow() - timedelta(hours=1),
        period_end=datetime.utcnow(),
        leaf_count=1,
        merkle_root="d" * 64,
        timeline_hash="timeline_hash_3",
        status="sealed"
    )
    session.add(timeline)
    await session.commit()
    await session.refresh(timeline)
    
    await witness_federation.request_witness_signature(session, timeline.id, witness.id)
    
    # Create a dummy receipt
    receipt = CommercialInferenceReceipt(
        client_id=str(uuid.uuid4()),
        model_name="gpt-4",
        backend_name="test-backend",
        receipt_hash="abc",
        prompt_hash="prompt_hash",
        response_hash="response_hash",
        detached_signature="sig"
    )
    session.add(receipt)
    await session.commit()
    await session.refresh(receipt)
    
    # Verify we can include witness info in exported proof
    # (Assuming execution_proofs.py will be updated to include it)
    quorum = await witness_federation.evaluate_witness_quorum(session, timeline.id)
    assert "signatures" in quorum
    assert len(quorum["signatures"]) == 1
