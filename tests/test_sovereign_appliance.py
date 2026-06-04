from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from app.core.config import get_settings
from app.db.base import Base
from app.services.inference import sovereign_appliance
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
async def test_ensure_appliance_profile(session: AsyncSession):
    profile = await sovereign_appliance.ensure_appliance_profile(session)
    assert profile.appliance_id == get_settings().commercial_appliance_id
    assert profile.deployment_tier == get_settings().commercial_appliance_deployment_tier
    assert profile.is_offline_first == True

@pytest.mark.asyncio
async def test_create_offline_sync_manifest(session: AsyncSession):
    manifest = await sovereign_appliance.create_offline_sync_manifest(
        session, "export", "models", "media-123"
    )
    assert manifest.sync_direction == "export"
    assert manifest.payload_type == "models"
    assert manifest.media_uuid == "media-123"
    assert manifest.is_verified == False

@pytest.mark.asyncio
async def test_stage_offline_model_bundle(session: AsyncSession):
    manifest = await sovereign_appliance.create_offline_sync_manifest(
        session, "import", "models"
    )
    bundle = await sovereign_appliance.stage_offline_model_bundle(
        session, "offline-gpt4", manifest.id
    )
    assert bundle.model_name == "offline-gpt4"
    assert bundle.promotion_status == "staged"
    assert bundle.bundle_hash is not None

@pytest.mark.asyncio
async def test_generate_offline_audit_package(session: AsyncSession):
    end = datetime.utcnow()
    start = end - timedelta(hours=24)
    package = await sovereign_appliance.generate_offline_audit_package(
        session, start, end
    )
    assert package.export_status == "generated"
    assert package.package_hash is not None

@pytest.mark.asyncio
async def test_verify_removable_media(session: AsyncSession):
    get_settings().commercial_appliance_require_removable_media = True
    manifest = await sovereign_appliance.create_offline_sync_manifest(
        session, "export", "audits", "usb-abc"
    )
    
    # Invalid media
    res_false = await sovereign_appliance.verify_removable_media(session, manifest.id, "usb-xyz")
    assert res_false == False
    
    # Valid media
    res_true = await sovereign_appliance.verify_removable_media(session, manifest.id, "usb-abc")
    assert res_true == True
    
    await session.refresh(manifest)
    assert manifest.is_verified == True
