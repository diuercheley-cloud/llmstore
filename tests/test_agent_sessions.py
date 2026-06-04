import uuid
from datetime import timedelta

import pytest
from app.core.time import utc_now
from app.models.agent_sessions import AgentThreadMessage
from app.services.agents.sessions.agent_session_service import AgentSessionService
from app.services.agents.sessions.conversation_thread_service import ConversationThreadService
from app.services.agents.sessions.session_context_builder import SessionContextBuilder
from app.services.agents.sessions.session_history_policy import SessionHistoryPolicyService
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_agent_session_lifecycle(session: AsyncSession):
    svc = AgentSessionService(session)
    tenant_id = "test-tenant"
    agent_id = uuid.uuid4()
    
    # 1. Create Session
    session_obj = await svc.create_session(
        tenant_id=tenant_id,
        agent_id=agent_id,
        title="Test Session"
    )
    assert session_obj.id is not None
    assert session_obj.tenant_id == tenant_id
    assert session_obj.status == "active"
    
    # 2. Send Message
    thread_svc = ConversationThreadService(session)
    msg = await thread_svc.add_message(
        session_id=session_obj.id,
        role="user",
        content="Hello Agent"
    )
    assert msg.session_id == session_obj.id
    assert msg.content == "Hello Agent"
    
    # 3. Recover History
    history = await thread_svc.get_messages(session_obj.id)
    assert len(history) == 1
    assert history[0].content == "Hello Agent"
    
    # 4. Context Builder
    builder = SessionContextBuilder(session)
    context = await builder.build_context(session_obj.id)
    assert context["message_count"] == 1
    assert context["history"][0]["content"] == "Hello Agent"
    
    # 5. Summarization check
    policy_svc = SessionHistoryPolicyService(session)
    # Add many messages to trigger summary
    for i in range(55):
        await thread_svc.add_message(session_obj.id, "user", f"Msg {i}")
    
    assert await policy_svc.should_summarize(session_obj.id) is True
    summary = await svc.check_and_trigger_summarization(session_obj.id)
    assert summary is not None
    assert session_obj.summary is not None
    
    # 6. Tenant Isolation
    session_b = await svc.get_session(session_obj.id, tenant_id="other-tenant")
    assert session_b is None
    
    # 7. Retention Policy
    # Manually set a message to be old
    old_msg = await thread_svc.add_message(session_obj.id, "user", "Old Message")
    old_msg.created_at = utc_now() - timedelta(days=100)
    await session.commit()
    
    # session.retention_policy is already {"retention_days": 90}
    totals = await svc.apply_retention_policies()
    assert totals["messages_deleted"] >= 1
    
    # Verify old message is gone
    res = await session.get(AgentThreadMessage, old_msg.id)
    assert res is None

@pytest.mark.asyncio
async def test_session_redaction(session: AsyncSession):
    svc = AgentSessionService(session)
    session_obj = await svc.create_session("tenant", uuid.uuid4())
    thread_svc = ConversationThreadService(session)
    
    await thread_svc.add_message(session_obj.id, "user", "My email is test@example.com and key is sk-12345678901234567890")
    
    builder = SessionContextBuilder(session)
    context = await builder.build_context(session_obj.id, redact_pii=True, redact_secrets=True)
    
    redacted_content = context["history"][0]["content"]
    assert "test@example.com" not in redacted_content
    assert "[EMAIL REDACTED]" in redacted_content
    assert "sk-12345678901234567890" not in redacted_content
    assert "[REDACTED]" in redacted_content
