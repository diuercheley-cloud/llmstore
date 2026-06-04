import os
from datetime import timedelta
from unittest.mock import patch

import pytest
import pytest_asyncio
from app.core.config import get_settings
from app.core.time import utc_now
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.connector_auth import ConnectorOAuthClient, ConnectorOAuthToken
from app.services.agents.connectors.connector_scopes import ConnectorScopeManager
from app.services.agents.connectors.connector_secret_store import connector_secret_store
from app.services.agents.connectors.connector_token_rotation import TokenRotationService
from app.services.agents.connectors.oauth import OAuthService


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def db_session():
    async with SessionLocal() as session:
        yield session

@pytest.mark.asyncio
async def test_token_encryption_no_leakage():
    raw_token = "sk-12345"
    encrypted = connector_secret_store.encrypt(raw_token)
    assert encrypted != raw_token.encode()
    assert connector_secret_store.decrypt(encrypted) == raw_token

@pytest.mark.asyncio
async def test_scope_enforcement(db_session):
    manager = ConnectorScopeManager(db_session)
    await manager.create_policy("t1", "github", "create_issue", ["repo"])
    
    # 1. Sufficient scope
    assert await manager.check_scopes("t1", "github", "create_issue", ["repo", "user"]) is True
    
    # 2. Insufficient scope
    assert await manager.check_scopes("t1", "github", "create_issue", ["user"]) is False

@pytest.mark.asyncio
async def test_token_refresh_simulation(db_session):
    service = TokenRotationService(db_session)
    
    # Create expired token
    client = ConnectorOAuthClient(
        tenant_id="t1", connector_name="github", client_id="c1", 
        client_secret_encrypted=b"s", auth_url="a", token_url="t", redirect_uri="r"
    )
    db_session.add(client)
    await db_session.flush()
    
    token = ConnectorOAuthToken(
        client_id=client.id, tenant_id="t1", 
        access_token_encrypted=connector_secret_store.encrypt("old"),
        refresh_token_encrypted=connector_secret_store.encrypt("refresh"),
        expires_at=utc_now() - timedelta(minutes=1),
        status="active"
    )
    db_session.add(token)
    await db_session.commit()
    
    new_access = await service.refresh_token_if_needed(token.id)
    assert new_access is not None
    assert "refreshed_access_" in new_access

@pytest.mark.asyncio
async def test_oauth_disabled_by_default(db_session):
    service = OAuthService(db_session)
    # Ensure flag is false
    with patch.dict(os.environ, {"AGENT_CONNECTOR_OAUTH_ENABLED": "false"}):
        get_settings.cache_clear()
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await service.start_flow("t1", "github")
        assert exc.value.status_code == 403

import pytest_asyncio
