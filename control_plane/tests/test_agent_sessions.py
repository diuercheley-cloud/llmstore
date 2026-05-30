# Owner: agent-platform
import uuid
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utc_now
from app.models.agent_sessions import (
    AgentSession,
    AgentConversationThread,
    AgentThreadMessage,
    AgentSessionRun,
    AgentSessionSummary,
)
from app.services.agents.sessions.agent_session_service import (
    AgentSessionService,
    SessionNotFoundError,
)
from app.services.agents.sessions.conversation_thread_service import (
    ConversationThreadService,
)
from app.services.agents.sessions.session_context_builder import SessionContextBuilder
from app.services.agents.sessions.session_history_policy import (
    SessionHistoryPolicyService,
    SUMMARY_TRIGGER_MESSAGE_COUNT,
)


@pytest.fixture
def mock_db():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def session_service(mock_db):
    return AgentSessionService(mock_db)


@pytest.fixture
def thread_service(mock_db):
    return ConversationThreadService(mock_db)


@pytest.fixture
def context_builder(mock_db):
    return SessionContextBuilder(mock_db)


@pytest.fixture
def policy_service(mock_db):
    return SessionHistoryPolicyService(mock_db)


@pytest.fixture
def sample_agent_id():
    return uuid.uuid4()


@pytest.fixture
def sample_tenant_a():
    return "tenant-a"


@pytest.fixture
def sample_tenant_b():
    return "tenant-b"


class TestCreateSession:
    async def test_create_session_success(self, session_service, mock_db, sample_agent_id, sample_tenant_a):
        session = await session_service.create_session(
            tenant_id=sample_tenant_a,
            agent_id=sample_agent_id,
            title="Test Session",
        )
        assert session.tenant_id == sample_tenant_a
        assert session.agent_id == sample_agent_id
        assert session.title == "Test Session"
        assert session.status == "active"
        assert session.retention_policy == {"retention_days": 90}
        mock_db.add.assert_called()
        mock_db.flush.assert_awaited()
        mock_db.commit.assert_awaited()
        mock_db.refresh.assert_awaited_with(session)

    async def test_create_session_with_user(self, session_service, mock_db, sample_agent_id, sample_tenant_a):
        session = await session_service.create_session(
            tenant_id=sample_tenant_a,
            agent_id=sample_agent_id,
            user_id="user-123",
            title="Session with User",
        )
        assert session.user_id == "user-123"

    async def test_create_session_custom_retention(self, session_service, mock_db, sample_agent_id, sample_tenant_a):
        retention = {"retention_days": 180, "keep_summaries": False}
        session = await session_service.create_session(
            tenant_id=sample_tenant_a,
            agent_id=sample_agent_id,
            retention_policy=retention,
        )
        assert session.retention_policy == retention


class TestGetSession:
    async def test_get_session_found(self, session_service, mock_db, sample_tenant_a):
        session_id = uuid.uuid4()
        mock_session = MagicMock(spec=AgentSession)
        mock_session.id = session_id
        mock_session.tenant_id = sample_tenant_a

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_session
        mock_db.execute.return_value = mock_result

        result = await session_service.get_session(session_id, sample_tenant_a)
        assert result is not None
        assert result.id == session_id

    async def test_get_session_not_found(self, session_service, mock_db, sample_tenant_a):
        session_id = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await session_service.get_session(session_id, sample_tenant_a)
        assert result is None

    async def test_tenant_isolation(self, session_service, mock_db, sample_tenant_a, sample_tenant_b):
        session_id = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await session_service.get_session(session_id, sample_tenant_b)
        assert result is None


class TestAddMessage:
    async def test_add_message_success(self, thread_service, mock_db):
        session_id = uuid.uuid4()
        message = await thread_service.add_message(
            session_id=session_id,
            role="user",
            content="Hello, agent!",
        )
        assert message.session_id == session_id
        assert message.role == "user"
        assert message.content == "Hello, agent!"
        assert message.content_hash is not None
        assert message.thread_id is not None
        mock_db.add.assert_called()
        mock_db.flush.assert_awaited()

    async def test_add_message_with_run_id(self, thread_service, mock_db):
        session_id = uuid.uuid4()
        run_id = uuid.uuid4()
        message = await thread_service.add_message(
            session_id=session_id,
            role="assistant",
            content="Response",
            run_id=run_id,
        )
        assert message.run_id == run_id
        assert message.role == "assistant"

    async def test_add_message_thread_creation(self, thread_service, mock_db):
        session_id = uuid.uuid4()
        message = await thread_service.add_message(
            session_id=session_id,
            role="user",
            content="First message",
        )
        assert message.thread_id is not None

    async def test_get_messages_empty(self, thread_service, mock_db):
        session_id = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        messages = await thread_service.get_messages(session_id)
        assert messages == []

    async def test_get_messages_order(self, thread_service, mock_db):
        session_id = uuid.uuid4()
        msg1 = MagicMock(spec=AgentThreadMessage)
        msg1.created_at = utc_now()
        msg2 = MagicMock(spec=AgentThreadMessage)
        msg2.created_at = utc_now() + timedelta(seconds=1)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [msg1, msg2]
        mock_db.execute.return_value = mock_result

        messages = await thread_service.get_messages(session_id)
        assert len(messages) == 2


class TestSessionRun:
    async def test_link_run_to_session(self, session_service, mock_db):
        session_id = uuid.uuid4()
        run_id = uuid.uuid4()

        mock_link = MagicMock(spec=AgentSessionRun)
        mock_link.session_id = session_id
        mock_link.run_id = run_id
        mock_db.refresh.return_value = mock_link

        link = await session_service.link_run_to_session(session_id, run_id)
        assert link is not None

    async def test_list_session_runs(self, session_service, mock_db, sample_tenant_a):
        session_id = uuid.uuid4()
        mock_session = MagicMock(spec=AgentSession)
        mock_session.id = session_id
        mock_session.tenant_id = sample_tenant_a

        get_result = MagicMock()
        get_result.scalar_one_or_none.return_value = mock_session
        mock_db.execute.return_value = get_result

        mock_runs = [MagicMock(spec=AgentSessionRun), MagicMock(spec=AgentSessionRun)]
        runs_result = MagicMock()
        runs_result.scalars.return_value.all.return_value = mock_runs
        mock_db.execute.return_value = runs_result

        runs = await session_service.get_session_runs(session_id, sample_tenant_a)
        assert len(runs) == 2


class TestDeleteSession:
    async def test_delete_session_success(self, session_service, mock_db, sample_tenant_a):
        session_id = uuid.uuid4()
        mock_session = MagicMock(spec=AgentSession)
        mock_session.id = session_id
        mock_session.tenant_id = sample_tenant_a

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_session
        mock_db.execute.return_value = mock_result

        result = await session_service.delete_session(session_id, sample_tenant_a)
        assert result is True
        mock_db.delete.assert_awaited_with(mock_session)
        mock_db.commit.assert_awaited()

    async def test_delete_session_not_found(self, session_service, mock_db, sample_tenant_a):
        session_id = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await session_service.delete_session(session_id, sample_tenant_a)
        assert result is False


class TestSessionContextBuilder:
    async def test_build_context_no_messages(self, context_builder, mock_db):
        session_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        context = await context_builder.build_context(session_id, max_messages=10)
        assert context["session_id"] == str(session_id)
        assert context["history"] == []
        assert context["message_count"] == 0

    async def test_build_context_redacts_secrets(self, context_builder, mock_db):
        session_id = uuid.uuid4()
        mock_msg = MagicMock(spec=AgentThreadMessage)
        mock_msg.role = "user"
        mock_msg.content = "My API key is sk-abc123def456ghi789"
        mock_msg.metadata = None
        mock_msg.id = uuid.uuid4()
        mock_msg.session_id = session_id
        mock_msg.thread_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_msg]
        mock_db.execute.return_value = mock_result

        context = await context_builder.build_context(session_id, redact_secrets=True, redact_pii=False)
        assert "[REDACTED]" in context["history"][0]["content"]
        assert "sk-abc123def456ghi789" not in context["history"][0]["content"]

    async def test_build_context_redacts_pii(self, context_builder, mock_db):
        session_id = uuid.uuid4()
        mock_msg = MagicMock(spec=AgentThreadMessage)
        mock_msg.role = "user"
        mock_msg.content = "Email me at test@example.com"
        mock_msg.metadata = None
        mock_msg.id = uuid.uuid4()
        mock_msg.session_id = session_id
        mock_msg.thread_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_msg]
        mock_db.execute.return_value = mock_result

        context = await context_builder.build_context(session_id, redact_secrets=False, redact_pii=True)
        assert "[EMAIL REDACTED]" in context["history"][0]["content"]
        assert "test@example.com" not in context["history"][0]["content"]

    async def test_build_context_with_summary(self, context_builder, mock_db):
        session_id = uuid.uuid4()
        mock_msg = MagicMock(spec=AgentThreadMessage)
        mock_msg.role = "user"
        mock_msg.content = "Hello"
        mock_msg.metadata = None
        mock_msg.id = uuid.uuid4()
        mock_msg.session_id = session_id
        mock_msg.thread_id = uuid.uuid4()

        mock_msg_result = MagicMock()
        mock_msg_result.scalars.return_value.all.return_value = [mock_msg]
        mock_db.execute.return_value = mock_msg_result

        mock_summary = MagicMock(spec=AgentSessionSummary)
        mock_summary.summary_text = "User said hello"
        mock_summary.message_count = 1

        mock_sum_result = MagicMock()
        mock_sum_result.scalar_one_or_none.return_value = mock_summary

        async def execute_side_effect(*args, **kwargs):
            return mock_msg_result

        from sqlalchemy import desc

        async def execute_with_summary(*args, **kwargs):
            query = args[0]
            query_str = str(query) if hasattr(query, '__str__') else str(query)
            if 'agent_session_summaries' in query_str:
                return mock_sum_result
            return mock_msg_result

        mock_db.execute = AsyncMock(side_effect=execute_with_summary)

        context = await context_builder.build_context(session_id, include_summary=True)
        assert context["summary"] == "User said hello"


class TestSessionHistoryPolicy:
    async def test_should_summarize_false(self, policy_service, mock_db):
        session_id = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 10
        mock_db.execute.return_value = mock_result

        result = await policy_service.should_summarize(session_id)
        assert result is False

    async def test_should_summarize_true(self, policy_service, mock_db):
        session_id = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.scalar.return_value = SUMMARY_TRIGGER_MESSAGE_COUNT + 1
        mock_db.execute.return_value = mock_result

        result = await policy_service.should_summarize(session_id)
        assert result is True

    async def test_apply_retention_deletes_old_messages(self, policy_service, mock_db):
        session = MagicMock(spec=AgentSession)
        session.id = uuid.uuid4()
        session.retention_policy = {"retention_days": 1}
        session.status = "active"

        mock_count = MagicMock()
        mock_count.scalar.return_value = 5
        mock_db.execute.return_value = mock_count

        mock_delete = MagicMock()
        mock_delete.rowcount = 5
        mock_db.execute.return_value = mock_delete

        result = await policy_service.apply_session_retention(session, dry_run=False)
        assert result["messages_deleted"] == 5

    async def test_apply_retention_dry_run(self, policy_service, mock_db):
        session = MagicMock(spec=AgentSession)
        session.id = uuid.uuid4()
        session.retention_policy = {"retention_days": 1}
        session.status = "active"

        mock_count = MagicMock()
        mock_count.scalar.return_value = 5
        mock_db.execute.return_value = mock_count

        result = await policy_service.apply_session_retention(session, dry_run=True)
        assert result["messages_deleted"] == 0  # dry_run: counted but not deleted


class TestTenantIsolation:
    async def test_tenant_a_cannot_access_tenant_b_session(self, session_service, mock_db):
        session_id = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await session_service.get_session(
            session_id=session_id,
            tenant_id="tenant-b",
        )
        assert result is None

    async def test_list_sessions_scoped_by_tenant(self, session_service, mock_db, sample_tenant_a):
        mock_sessions = [
            MagicMock(spec=AgentSession),
            MagicMock(spec=AgentSession),
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_sessions
        mock_db.execute.return_value = mock_result

        sessions = await session_service.list_sessions(tenant_id=sample_tenant_a)
        assert len(sessions) == 2

    async def test_delete_session_tenant_isolation(self, session_service, mock_db, sample_tenant_a, sample_tenant_b):
        session_id = uuid.uuid4()
        mock_tenant_a_session = MagicMock(spec=AgentSession)
        mock_tenant_a_session.id = session_id
        mock_tenant_a_session.tenant_id = sample_tenant_a

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await session_service.delete_session(session_id, sample_tenant_b)
        assert result is False  # tenant_b cannot delete tenant_a's session


class TestUpdateSession:
    async def test_update_title(self, session_service, mock_db, sample_tenant_a):
        session_id = uuid.uuid4()
        mock_session = MagicMock(spec=AgentSession)
        mock_session.id = session_id
        mock_session.tenant_id = sample_tenant_a
        mock_session.metadata = {}

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_session
        mock_db.execute.return_value = mock_result

        result = await session_service.update_session(
            session_id, sample_tenant_a, title="Updated Title"
        )
        assert mock_session.title == "Updated Title"

    async def test_update_status_to_archived(self, session_service, mock_db, sample_tenant_a):
        session_id = uuid.uuid4()
        mock_session = MagicMock(spec=AgentSession)
        mock_session.id = session_id
        mock_session.tenant_id = sample_tenant_a
        mock_session.status = "active"
        mock_session.metadata = {}

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_session
        mock_db.execute.return_value = mock_result

        result = await session_service.archive_session(session_id, sample_tenant_a)
        assert mock_session.status == "archived"
