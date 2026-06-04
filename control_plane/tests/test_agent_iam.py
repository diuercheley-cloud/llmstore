import os
import uuid
from unittest.mock import patch

import pytest
import pytest_asyncio
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.agent_iam import (
    AgentCredentialAuditEvent,
    AgentDelegatedToken,
)
from app.models.agents import AgentDefinition
from app.services.agents.iam.agent_identity import AgentIdentityService
from app.services.agents.iam.agent_scopes import AgentScopeManager
from app.services.agents.iam.credential_broker import CredentialBroker
from app.services.agents.iam.delegated_tokens import DelegatedTokenService
from app.services.agents.iam.service_principal import ServicePrincipalService
from app.services.agents.iam.token_exchange import TokenExchangeService
from sqlalchemy import select


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

@pytest_asyncio.fixture
async def sample_agent(db_session):
    agent = AgentDefinition(
        id=uuid.uuid4(),
        name="SecurityAgent",
        version="1.0.0",
        instructions="Analyze logs.",
        model_id="gpt-4",
        owner="security-team",
        tenant_id="tenant-a"
    )
    db_session.add(agent)
    await db_session.commit()
    return agent

@pytest.mark.asyncio
async def test_service_principal_creation_and_rotation(db_session, sample_agent):
    sp_service = ServicePrincipalService(db_session)

    # 1. Create SP
    sp, raw_secret = await sp_service.create_service_principal(
        tenant_id="tenant-a",
        agent_id=sample_agent.id,
        description="SP for logs agent"
    )
    await db_session.commit()

    assert sp.client_id.startswith("sp-")
    assert raw_secret.startswith("sec_")
    assert sp.client_secret_hash != raw_secret
    assert sp.status == "active"

    # Verify subsequent fetch does not return raw secret
    fetched_sp = await sp_service.get_service_principal("tenant-a", sample_agent.id)
    assert fetched_sp is not None
    assert fetched_sp.client_id == sp.client_id
    assert not hasattr(fetched_sp, "client_secret") or fetched_sp.client_secret is None

    # Authenticate successfully
    auth_sp = await sp_service.authenticate(sp.client_id, raw_secret)
    assert auth_sp is not None
    assert auth_sp.agent_id == sample_agent.id

    # Authenticate failure with wrong secret
    auth_sp_fail = await sp_service.authenticate(sp.client_id, "wrong_secret")
    assert auth_sp_fail is None

    # Rotate secret
    new_raw_secret = await sp_service.rotate_secret("tenant-a", sample_agent.id)
    await db_session.commit()

    assert new_raw_secret != raw_secret
    # Authenticate with new secret succeeds
    assert await sp_service.authenticate(sp.client_id, new_raw_secret) is not None
    # Authenticate with old secret fails
    assert await sp_service.authenticate(sp.client_id, raw_secret) is None

@pytest.mark.asyncio
async def test_token_grant_and_exchange(db_session, sample_agent):
    exchange_service = TokenExchangeService(db_session)

    # Create user grant
    grant = await exchange_service.create_token_grant(
        tenant_id="tenant-a",
        agent_id=sample_agent.id,
        user_id="user-123",
        connector_id="github",
        scopes=["github:read", "github:write"]
    )
    await db_session.commit()

    assert grant.is_revoked is False
    assert grant.connector_id == "github"

    # Exchange grant for token
    token, raw_token = await exchange_service.exchange_grant_for_token(
        tenant_id="tenant-a",
        agent_id=sample_agent.id,
        user_id="user-123",
        connector_id="github",
        requested_scopes=["github:read"]
    )
    await db_session.commit()

    assert raw_token.startswith("agt_")
    assert token.token_type == "connector"
    assert token.scopes == [{"connector": "github", "action": "github:read"}]

    # Exchange fails if requested scopes exceed grant scopes
    with pytest.raises(PermissionError):
        await exchange_service.exchange_grant_for_token(
            tenant_id="tenant-a",
            agent_id=sample_agent.id,
            user_id="user-123",
            connector_id="github",
            requested_scopes=["github:admin"]
        )

@pytest.mark.asyncio
async def test_scope_matching():
    # Mock token
    token = AgentDelegatedToken(
        tenant_id="tenant-a",
        agent_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        scopes=[{"connector": "slack", "action": "post_message"}]
    )

    manager = AgentScopeManager()
    agent_id = uuid.UUID("11111111-1111-1111-1111-111111111111")

    # Match exact
    assert manager.match_scope(token, "tenant-a", agent_id, "slack", "post_message") is True

    # Insufficient scope (action mismatch)
    assert manager.match_scope(token, "tenant-a", agent_id, "slack", "search_messages") is False

    # Insufficient scope (connector mismatch)
    assert manager.match_scope(token, "tenant-a", agent_id, "github", "post_message") is False

    # Agent mismatch
    other_agent = uuid.uuid4()
    assert manager.match_scope(token, "tenant-a", other_agent, "slack", "post_message") is False

@pytest.mark.asyncio
async def test_tenant_isolation_cross_tenant_grant_blocks(db_session, sample_agent):
    exchange_service = TokenExchangeService(db_session)

    # Grant on tenant-a
    grant = await exchange_service.create_token_grant(
        tenant_id="tenant-a",
        agent_id=sample_agent.id,
        user_id="user-123",
        connector_id="slack",
        scopes=["slack:read"]
    )
    await db_session.commit()

    # Attempt to exchange on tenant-b should block
    with pytest.raises(PermissionError):
        await exchange_service.exchange_grant_for_token(
            tenant_id="tenant-b",
            agent_id=sample_agent.id,
            user_id="user-123",
            connector_id="slack",
            requested_scopes=["slack:read"]
        )

@pytest.mark.asyncio
async def test_token_expiration_and_revocation(db_session, sample_agent):
    token_service = DelegatedTokenService(db_session)

    # 1. Active Token
    token, raw_token = await token_service.create_token(
        tenant_id="tenant-a",
        agent_id=sample_agent.id,
        scopes=[{"connector": "github", "action": "read"}],
        expires_in_seconds=3600
    )
    await db_session.commit()

    verified = await token_service.verify_token(raw_token)
    assert verified is not None
    assert verified.id == token.id

    # 2. Expired Token
    expired_token, raw_expired = await token_service.create_token(
        tenant_id="tenant-a",
        agent_id=sample_agent.id,
        scopes=[{"connector": "github", "action": "read"}],
        expires_in_seconds=-10
    )
    await db_session.commit()

    assert await token_service.verify_token(raw_expired) is None

    # 3. Revoked Token
    await token_service.revoke_token(token.id, "tenant-a")
    await db_session.commit()

    assert await token_service.verify_token(raw_token) is None

@pytest.mark.asyncio
async def test_credential_broker_write_restrictions(db_session, sample_agent):
    broker = CredentialBroker(db_session)
    identity_service = AgentIdentityService(db_session)
    exchange_service = TokenExchangeService(db_session)

    # Create grant and exchange token
    await exchange_service.create_token_grant(
        tenant_id="tenant-a",
        agent_id=sample_agent.id,
        user_id="user-123",
        connector_id="slack",
        scopes=["post_message", "search_messages"]
    )
    token, raw_token = await exchange_service.exchange_grant_for_token(
        tenant_id="tenant-a",
        agent_id=sample_agent.id,
        user_id="user-123",
        connector_id="slack",
        requested_scopes=["post_message", "search_messages"]
    )
    await db_session.commit()

    # 1. Read action (search_messages) works without identity
    assert await broker.validate_access(
        tenant_id="tenant-a",
        agent_id=sample_agent.id,
        connector_name="slack",
        action="search_messages",
        token_string=raw_token
    ) is True

    # 2. Write action (post_message) fails because agent has no identity binding
    with pytest.raises(PermissionError) as exc:
        await broker.validate_access(
            tenant_id="tenant-a",
            agent_id=sample_agent.id,
            connector_name="slack",
            action="post_message",
            token_string=raw_token
        )
    assert "does not have a bound identity" in str(exc.value)

    # Bind identity to agent
    await identity_service.bind_identity(
        tenant_id="tenant-a",
        agent_id=sample_agent.id,
        identity_provider="sovereign",
        external_id="did:key:z6MkuS"
    )
    await db_session.commit()

    # 3. Write action succeeds now that agent has bound identity
    assert await broker.validate_access(
        tenant_id="tenant-a",
        agent_id=sample_agent.id,
        connector_name="slack",
        action="post_message",
        token_string=raw_token
    ) is True

@pytest.mark.asyncio
async def test_production_service_principal_enforcement(db_session, sample_agent):
    broker = CredentialBroker(db_session)
    identity_service = AgentIdentityService(db_session)
    exchange_service = TokenExchangeService(db_session)
    sp_service = ServicePrincipalService(db_session)

    # Bind identity
    await identity_service.bind_identity(
        tenant_id="tenant-a",
        agent_id=sample_agent.id,
        identity_provider="sovereign"
    )

    # Create grant and token
    await exchange_service.create_token_grant(
        tenant_id="tenant-a",
        agent_id=sample_agent.id,
        user_id="user-123",
        connector_id="slack",
        scopes=["post_message"]
    )
    token, raw_token = await exchange_service.exchange_grant_for_token(
        tenant_id="tenant-a",
        agent_id=sample_agent.id,
        user_id="user-123",
        connector_id="slack",
        requested_scopes=["post_message"]
    )
    await db_session.commit()

    # Set prod mode
    with patch.dict(os.environ, {"ENV": "production"}):
        # 1. Fails in prod because SP is missing
        with pytest.raises(PermissionError) as exc:
            await broker.validate_access(
                tenant_id="tenant-a",
                agent_id=sample_agent.id,
                connector_name="slack",
                action="post_message",
                token_string=raw_token
            )
        assert "requires agent" in str(exc.value)

        # 2. Add SP
        await sp_service.create_service_principal("tenant-a", sample_agent.id)
        await db_session.commit()

        # 3. Succeeds in prod now that SP exists
        assert await broker.validate_access(
            tenant_id="tenant-a",
            agent_id=sample_agent.id,
            connector_name="slack",
            action="post_message",
            token_string=raw_token
        ) is True

@pytest.mark.asyncio
async def test_redaction_in_audit_logs(db_session, sample_agent):
    from app.services.agents.iam.iam_audit import IAMAuditService
    audit = IAMAuditService(db_session)

    await audit.log_event(
        tenant_id="tenant-a",
        event_type="test_leakage",
        agent_id=sample_agent.id,
        details={
            "token": "agt_secrettokenvalue12345",
            "api_key": "sk-local-secretkey12345",
            "connector": "slack"
        }
    )
    await db_session.commit()

    # Query audit events
    stmt = select(AgentCredentialAuditEvent).where(AgentCredentialAuditEvent.event_type == "test_leakage")
    res = await db_session.execute(stmt)
    event = res.scalar_one()

    # Verify redaction
    assert "agt_secrettokenvalue12345" not in event.details["token"]
    assert "[REDACTED]" in event.details["token"]
    assert "[REDACTED]" in event.details["api_key"]
    assert event.details["connector"] == "slack"

@pytest.mark.asyncio
async def test_manual_dev_test_token_support():
    token_service = DelegatedTokenService(None)
    
    # Verify mock generation format: manual_test_token_{tenant}_{agent_id}_{connector}_{action}
    agent_id = uuid.uuid4()
    raw_manual_token = f"manual_test_token_tenant-a_{agent_id}_slack_post_message"
    
    verified = await token_service.verify_token(raw_manual_token)
    assert verified is not None
    assert verified.tenant_id == "tenant-a"
    assert verified.agent_id == agent_id
    assert verified.token_type == "manual"
    assert verified.scopes == [{"connector": "slack", "action": "post_message"}]
