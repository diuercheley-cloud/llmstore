import pytest
import uuid
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agents import AgentA2ARegistration, AgentDelegationPolicy
from app.services.agents.a2a.a2a_server import A2AServerService
from app.services.agents.a2a.a2a_security import A2ASecurityService


@pytest.fixture(autouse=True)
def patch_a2a_checks():
    with patch.object(A2ASecurityService, "verify_a2a_enabled_or_raise"):
        with patch.object(A2ASecurityService, "verify_external_enabled_or_raise"):
            yield


@pytest.fixture
def mock_db():
    return MagicMock(spec=AsyncSession)


def _make_reg(agent_id=None, tenant_id="tenant-1", token="test-token"):
    return AgentA2ARegistration(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        agent_id=agent_id or uuid.uuid4(),
        auth_token=token,
        is_external=False,
    )


class TestA2AServerReceiveMessage:
    @pytest.mark.asyncio
    async def test_receive_message_success(self, mock_db):
        sender_reg = _make_reg()
        recipient_reg = _make_reg()
        msg_id = str(uuid.uuid4())

        payload = {
            "message_id": msg_id,
            "conversation_id": "conv-1",
            "sender_agent_id": str(sender_reg.agent_id),
            "recipient_agent_id": str(recipient_reg.agent_id),
            "content_type": "text/plain",
            "payload": {"text": "hello"},
            "timestamp": "2025-01-01T00:00:00+00:00",
            "signature": "valid-signature",
        }

        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalar_one_or_none=lambda: sender_reg),
            MagicMock(scalar_one_or_none=lambda: recipient_reg),
        ])

        with patch.object(A2ASecurityService, "authenticate_agent", AsyncMock(return_value=sender_reg)):
            with patch.object(A2ASecurityService, "verify_signature", return_value=True):
                with patch("app.services.agents.a2a.a2a_server.record_admin_audit_event", AsyncMock()):
                    result = await A2AServerService.receive_message(
                        db=mock_db, message_payload=payload, token=sender_reg.auth_token
                    )
                    assert result["status"] == "success"
                    assert result["message_id"] == msg_id

    @pytest.mark.asyncio
    async def test_receive_message_missing_signature(self, mock_db):
        payload = {
            "message_id": str(uuid.uuid4()),
            "conversation_id": "conv-1",
            "sender_agent_id": str(uuid.uuid4()),
            "recipient_agent_id": str(uuid.uuid4()),
            "payload": {},
        }
        with patch.object(A2ASecurityService, "authenticate_agent", AsyncMock(return_value=_make_reg())):
            with pytest.raises(HTTPException) as exc:
                await A2AServerService.receive_message(
                    db=mock_db, message_payload=payload, token="token"
                )
            assert exc.value.status_code == 400
            assert "Missing message signature" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_receive_message_missing_recipient(self, mock_db):
        payload = {
            "message_id": str(uuid.uuid4()),
            "conversation_id": "conv-1",
            "sender_agent_id": str(uuid.uuid4()),
            "payload": {},
            "signature": "sig",
        }
        with patch.object(A2ASecurityService, "authenticate_agent", AsyncMock(return_value=_make_reg())):
            with pytest.raises(HTTPException) as exc:
                await A2AServerService.receive_message(
                    db=mock_db, message_payload=payload, token="token"
                )
            assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_receive_message_recipient_not_registered(self, mock_db):
        sender_reg = _make_reg()
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: None))

        payload = {
            "message_id": str(uuid.uuid4()),
            "conversation_id": "c1",
            "sender_agent_id": str(sender_reg.agent_id),
            "recipient_agent_id": str(uuid.uuid4()),
            "payload": {},
            "signature": "sig",
        }

        with patch.object(A2ASecurityService, "authenticate_agent", AsyncMock(return_value=sender_reg)):
            with patch.object(A2ASecurityService, "verify_signature", return_value=True):
                with pytest.raises(HTTPException) as exc:
                    await A2AServerService.receive_message(
                        db=mock_db, message_payload=payload, token="token"
                    )
                assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_receive_message_invalid_signature(self, mock_db):
        sender_reg = _make_reg()
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: None))

        payload = {
            "message_id": str(uuid.uuid4()),
            "conversation_id": "c1",
            "sender_agent_id": str(sender_reg.agent_id),
            "recipient_agent_id": str(uuid.uuid4()),
            "payload": {},
            "signature": "invalid",
        }

        with patch.object(A2ASecurityService, "authenticate_agent", AsyncMock(return_value=sender_reg)):
            with patch.object(A2ASecurityService, "verify_signature", return_value=False):
                with pytest.raises(HTTPException) as exc:
                    await A2AServerService.receive_message(
                        db=mock_db, message_payload=payload, token="token"
                    )
                assert exc.value.status_code == 400
                assert "Invalid message signature" in str(exc.value.detail)


class TestA2AServerReceiveDelegation:
    @pytest.mark.asyncio
    async def test_receive_delegation_success(self, mock_db):
        delegator_id = uuid.uuid4()
        delegatee_id = uuid.uuid4()
        sender_reg = _make_reg(agent_id=delegator_id)
        delegatee_reg = _make_reg(agent_id=delegatee_id)

        payload = {
            "task_id": str(uuid.uuid4()),
            "delegator_agent_id": str(delegator_id),
            "delegatee_agent_id": str(delegatee_id),
            "task_description": "Process this task",
            "input_data": {"key": "value"},
            "timestamp": "2025-01-01T00:00:00+00:00",
            "signature": "valid-sig",
        }

        mock_policy = AgentDelegationPolicy(
            source_agent_id=delegator_id,
            target_agent_id=delegatee_id,
            tenant_id="tenant-1",
            is_active=True,
        )

        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalar_one_or_none=lambda: delegatee_reg),
            MagicMock(scalar_one_or_none=lambda: mock_policy),
        ])

        with patch.object(A2ASecurityService, "authenticate_agent", AsyncMock(return_value=sender_reg)):
            with patch.object(A2ASecurityService, "verify_signature", return_value=True):
                with patch("app.services.agents.a2a.a2a_server.record_admin_audit_event", AsyncMock()):
                    result = await A2AServerService.receive_delegation(
                        db=mock_db, delegation_payload=payload, token="token"
                    )
                    assert result["status"] == "success"
                    assert "task_id" in result

    @pytest.mark.asyncio
    async def test_receive_delegation_missing_signature(self, mock_db):
        payload = {
            "task_id": str(uuid.uuid4()),
            "delegator_agent_id": str(uuid.uuid4()),
            "delegatee_agent_id": str(uuid.uuid4()),
            "task_description": "Task",
            "input_data": {},
        }
        with patch.object(A2ASecurityService, "authenticate_agent", AsyncMock(return_value=_make_reg())):
            with pytest.raises(HTTPException) as exc:
                await A2AServerService.receive_delegation(
                    db=mock_db, delegation_payload=payload, token="token"
                )
            assert exc.value.status_code == 400
            assert "Missing delegation signature" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_receive_delegation_delegatee_not_registered(self, mock_db):
        sender_reg = _make_reg()
        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalar_one_or_none=lambda: sender_reg),
            MagicMock(scalar_one_or_none=lambda: None),
        ])

        payload = {
            "task_id": str(uuid.uuid4()),
            "delegator_agent_id": str(uuid.uuid4()),
            "delegatee_agent_id": str(uuid.uuid4()),
            "task_description": "Task",
            "input_data": {},
            "signature": "sig",
        }

        with patch.object(A2ASecurityService, "authenticate_agent", AsyncMock(return_value=sender_reg)):
            with patch.object(A2ASecurityService, "verify_signature", return_value=True):
                with pytest.raises(HTTPException) as exc:
                    await A2AServerService.receive_delegation(
                        db=mock_db, delegation_payload=payload, token="token"
                    )
                assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_receive_delegation_missing_policy(self, mock_db):
        delegator_id = uuid.uuid4()
        delegatee_id = uuid.uuid4()
        sender_reg = _make_reg(agent_id=delegator_id)
        delegatee_reg = _make_reg(agent_id=delegatee_id)

        payload = {
            "task_id": str(uuid.uuid4()),
            "delegator_agent_id": str(delegator_id),
            "delegatee_agent_id": str(delegatee_id),
            "task_description": "Task",
            "input_data": {},
            "signature": "sig",
        }

        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalar_one_or_none=lambda: delegatee_reg),
            MagicMock(scalar_one_or_none=lambda: None),
        ])

        with patch.object(A2ASecurityService, "authenticate_agent", AsyncMock(return_value=sender_reg)):
            with patch.object(A2ASecurityService, "verify_signature", return_value=True):
                with pytest.raises(HTTPException) as exc:
                    await A2AServerService.receive_delegation(
                        db=mock_db, delegation_payload=payload, token="token"
                    )
                assert exc.value.status_code == 403
                assert "does not exist" in str(exc.value.detail)
