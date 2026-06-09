import pytest
from app.db.session import get_db_session
from app.main import app
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_rate_limit_probe_requires_admin_token(isolated_db_url):
    from app.db.base import Base
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    
    engine = create_async_engine(isolated_db_url)
    testing_session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db_session():
        async with testing_session_local() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        # Try to create plan without admin token
        resp = await ac.post("/admin/billing/plans", json={"code": "hack", "name": "Hack Plan"})
        assert resp.status_code == 401
        
        # Try to create client without admin token
        resp_c = await ac.post("/admin/clients", json={"name": "hack-client"})
        assert resp_c.status_code == 401

    app.dependency_overrides.clear()
    await engine.dispose()

@pytest.mark.asyncio
async def test_rate_limit_probe_logs_sanitization():
    # Verify that the production-readiness script has the sanitization patterns.
    from pathlib import Path
    
    script_path = Path(__file__).parent.parent / "scripts" / "production-readiness-local.sh"
    content = script_path.read_text()
    
    # Check for SECRET_PATTERNS definition
    assert "SECRET_PATTERNS =" in content
    
    # Check for sk- key pattern
    assert "sk-[A-Za-z0-9_-]{10,}" in content
    
    # Verify the sanitization logic exists
    assert "def sanitize_text(value: str) -> str:" in content

