import pytest
from app.services.backup.restore_lock_service import MaintenanceMode, RestoreLockService
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest.fixture(autouse=True)
def setup_backup_keys(monkeypatch):
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", "a" * 32)
    monkeypatch.setenv("BACKUP_SIGNING_KEY", "b" * 32)


@pytest.mark.asyncio
async def test_concurrency_lock_and_release(isolated_db_url):
    engine = create_async_engine(isolated_db_url)
    session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with session_local() as session:
        lock_svc1 = RestoreLockService(session)
        lock_svc2 = RestoreLockService(session)

        # 1. First lock acquisition should succeed
        assert await lock_svc1.acquire_lock() is True
        assert MaintenanceMode.is_active() is True

        # 2. Second lock acquisition (concurrent) should fail
        assert await lock_svc2.acquire_lock() is False

        # 3. Lock release should set maintenance mode to false and free the lock
        await lock_svc1.release_lock()
        assert MaintenanceMode.is_active() is False

        # 4. Now second lock acquisition should succeed
        assert await lock_svc2.acquire_lock() is True
        await lock_svc2.release_lock()

    await engine.dispose()


@pytest.mark.asyncio
async def test_lock_release_on_exception(isolated_db_url):
    engine = create_async_engine(isolated_db_url)
    session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with session_local() as session:
        lock_svc = RestoreLockService(session)

        try:
            assert await lock_svc.acquire_lock() is True
            raise ValueError("Simulated restore exception")
        except ValueError:
            await lock_svc.release_lock()

        # Lock should be freed and maintenance mode off
        assert MaintenanceMode.is_active() is False
        assert await lock_svc.acquire_lock() is True
        await lock_svc.release_lock()

    await engine.dispose()


@pytest.mark.asyncio
async def test_maintenance_mode_middleware_routing(admin_client):
    from app.core.config import get_settings

    settings = get_settings()
    token = settings.admin_super_token or settings.admin_token or "test-admin-token"
    headers = {"X-Admin-Token": token}

    # By default, maintenance mode is not active
    MaintenanceMode.set_active(False)
    resp = await admin_client.post("/admin/invalid-test-endpoint-xyz", headers=headers)
    assert resp.status_code != 503

    # Activate maintenance mode
    MaintenanceMode.set_active(True)

    try:
        # GET on allowed health endpoints should be permitted
        resp_health = await admin_client.get("/health")
        assert resp_health.status_code == 200

        # POST / writes on blocked endpoints should return 503
        resp_blocked_write = await admin_client.post(
            "/admin/invalid-test-endpoint-xyz", headers=headers
        )
        assert resp_blocked_write.status_code == 503
        assert "Service Unavailable" in resp_blocked_write.json()["detail"]

        # GET on sensitive admin endpoints should also return 503
        resp_blocked_read = await admin_client.get(
            "/admin/invalid-test-endpoint-xyz", headers=headers
        )
        assert resp_blocked_read.status_code == 503
    finally:
        MaintenanceMode.set_active(False)
