import hashlib

import pytest
import pytest_asyncio
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.agents import AgentBundleSignature, AgentBundleVersion, AgentMarketplaceEntry
from app.services.agents.agent_bundle_verifier import AgentBundleVerifierService
from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        import app.models.agents  # noqa
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

async def _create_test_bundle(db: AsyncSession, content: bytes, signature_needed: bool = False):
    entry = AgentMarketplaceEntry(
        name="Test Agent",
        description="Test",
        author="test-author",
        category="test"
    )
    db.add(entry)
    await db.flush()

    checksum = hashlib.sha256(content).hexdigest()
    version = AgentBundleVersion(
        entry_id=entry.id,
        version="1.0.0",
        checksum_sha256=checksum,
        manifest_json={}
    )
    db.add(version)
    await db.flush()

    if signature_needed:
        sig = AgentBundleSignature(
            version_id=version.id,
            signature_type="ed25519",
            signature_value=f"sig:{checksum}:key-1",
            public_key_id="key-1",
            signed_by="test-author"
        )
        db.add(sig)
    
    await db.commit()
    return version

@pytest.mark.asyncio
async def test_checksum_mismatch_fails():
    async with SessionLocal() as db:
        content = b"original content"
        version = await _create_test_bundle(db, content)
        
        svc = AgentBundleVerifierService(db)
        # Verify with different content
        res = await svc.verify_bundle(version.id, b"tampered content")
        assert res["passed"] is False
        assert res["reason"] == "Checksum mismatch"

@pytest.mark.asyncio
async def test_signature_required_but_missing():
    settings = get_settings()
    settings.agent_bundle_signature_required = True
    
    async with SessionLocal() as db:
        content = b"content"
        version = await _create_test_bundle(db, content, signature_needed=False)
        
        svc = AgentBundleVerifierService(db)
        res = await svc.verify_bundle(version.id, content)
        assert res["passed"] is False
        assert "Signature required" in res["reason"]

@pytest.mark.asyncio
async def test_valid_signed_bundle_passes():
    settings = get_settings()
    settings.agent_bundle_signature_required = True
    
    async with SessionLocal() as db:
        content = b"content"
        version = await _create_test_bundle(db, content, signature_needed=True)
        
        svc = AgentBundleVerifierService(db)
        res = await svc.verify_bundle(version.id, content)
        assert res["passed"] is True
        assert res["is_signed"] is True

@pytest.mark.asyncio
async def test_trust_report_generation():
    async with SessionLocal() as db:
        content = b"content"
        version = await _create_test_bundle(db, content, signature_needed=True)
        
        svc = AgentBundleVerifierService(db)
        report = await svc.generate_trust_report(version.id)
        assert report.trust_score == 1.0
        assert report.is_signed is True
