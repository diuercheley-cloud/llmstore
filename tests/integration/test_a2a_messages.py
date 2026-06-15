import uuid
from datetime import UTC, datetime

from app.services.agents.a2a.a2a_messages import A2ADelegationPayload, A2AMessagePayload
from app.services.agents.a2a.a2a_security import A2ASecurityService


class TestA2AMessagePayload:
    def test_message_payload_defaults(self):
        msg = A2AMessagePayload(
            conversation_id="conv-1",
            sender_agent_id="agent-1",
            recipient_agent_id="agent-2",
            payload={"text": "hello"},
        )
        assert msg.message_id is not None
        assert uuid.UUID(msg.message_id)
        assert msg.conversation_id == "conv-1"
        assert msg.sender_agent_id == "agent-1"
        assert msg.recipient_agent_id == "agent-2"
        assert msg.content_type == "text/plain"
        assert msg.payload == {"text": "hello"}
        assert isinstance(msg.timestamp, datetime)
        assert msg.signature is None

    def test_message_payload_with_signature(self):
        msg = A2AMessagePayload(
            conversation_id="conv-1",
            sender_agent_id="agent-1",
            recipient_agent_id="agent-2",
            payload={"data": 42},
            signature="abc123",
        )
        assert msg.signature == "abc123"

    def test_message_payload_serialization_roundtrip(self):
        msg = A2AMessagePayload(
            conversation_id="conv-1",
            sender_agent_id="agent-1",
            recipient_agent_id="agent-2",
            payload={"text": "hello"},
            content_type="application/json",
        )
        data = msg.model_dump()
        restored = A2AMessagePayload(**data)
        assert restored.conversation_id == msg.conversation_id
        assert restored.sender_agent_id == msg.sender_agent_id
        assert restored.payload == msg.payload

    def test_message_payload_unique_ids(self):
        msgs = [
            A2AMessagePayload(
                conversation_id="c", sender_agent_id="s", recipient_agent_id="r", payload={}
            )
            for _ in range(100)
        ]
        ids = [m.message_id for m in msgs]
        assert len(set(ids)) == 100

    def test_message_payload_timestamp_utc(self):
        msg = A2AMessagePayload(
            conversation_id="c", sender_agent_id="s", recipient_agent_id="r", payload={}
        )
        assert msg.timestamp.tzinfo is not None


class TestA2ADelegationPayload:
    def test_delegation_payload_defaults(self):
        delegation = A2ADelegationPayload(
            delegator_agent_id="agent-1",
            delegatee_agent_id="agent-2",
            task_description="Process data",
            input_data={"file": "data.csv"},
        )
        assert delegation.task_id is not None
        assert uuid.UUID(delegation.task_id)
        assert delegation.delegator_agent_id == "agent-1"
        assert delegation.delegatee_agent_id == "agent-2"
        assert delegation.task_description == "Process data"
        assert delegation.input_data == {"file": "data.csv"}
        assert delegation.signature is None

    def test_delegation_payload_with_signature(self):
        delegation = A2ADelegationPayload(
            delegator_agent_id="agent-1",
            delegatee_agent_id="agent-2",
            task_description="Task",
            input_data={},
            signature="sig456",
        )
        assert delegation.signature == "sig456"

    def test_delegation_payload_serialization(self):
        delegation = A2ADelegationPayload(
            delegator_agent_id="d1",
            delegatee_agent_id="d2",
            task_description="Test",
            input_data={"key": "value"},
        )
        data = delegation.model_dump()
        restored = A2ADelegationPayload(**data)
        assert restored.delegator_agent_id == "d1"
        assert restored.task_description == "Test"


class TestA2ASignatures:
    def test_sign_and_verify_message(self):
        secret = "test-secret-key-123"
        msg = A2AMessagePayload(
            conversation_id="conv-1",
            sender_agent_id="agent-1",
            recipient_agent_id="agent-2",
            payload={"action": "ping"},
        )
        payload_dict = msg.model_dump()
        payload_dict["timestamp"] = payload_dict["timestamp"].isoformat()
        signature = A2ASecurityService.generate_signature(payload_dict, secret)
        payload_dict["signature"] = signature
        assert A2ASecurityService.verify_signature(payload_dict, secret, signature)

    def test_signature_fails_with_wrong_key(self):
        secret = "correct-key"
        wrong_secret = "wrong-key"
        payload = {
            "task_id": str(uuid.uuid4()),
            "delegator_agent_id": "agent-1",
            "delegatee_agent_id": "agent-2",
            "task_description": "Test",
            "input_data": {},
            "timestamp": datetime.now(UTC).isoformat(),
        }
        signature = A2ASecurityService.generate_signature(payload, secret)
        assert not A2ASecurityService.verify_signature(payload, wrong_secret, signature)

    def test_signature_fails_with_tampered_payload(self):
        secret = "test-key"
        payload = {
            "message_id": str(uuid.uuid4()),
            "conversation_id": "c1",
            "sender_agent_id": "s1",
            "recipient_agent_id": "r1",
            "content_type": "text/plain",
            "payload": {"text": "original"},
            "timestamp": datetime.now(UTC).isoformat(),
        }
        signature = A2ASecurityService.generate_signature(payload, secret)
        payload["payload"] = {"text": "tampered"}
        assert not A2ASecurityService.verify_signature(payload, secret, signature)

    def test_signature_excludes_signature_field(self):
        secret = "test-key"
        payload = {
            "message_id": str(uuid.uuid4()),
            "conversation_id": "c1",
            "sender_agent_id": "s1",
            "recipient_agent_id": "r1",
            "payload": {"text": "hello"},
            "timestamp": datetime.now(UTC).isoformat(),
        }
        sig1 = A2ASecurityService.generate_signature(payload, secret)
        payload_with_sig = {**payload, "signature": sig1}
        sig2 = A2ASecurityService.generate_signature(payload_with_sig, secret)
        assert sig1 == sig2

    def test_invalid_signature_rejected(self):
        secret = "test-key"
        payload = {
            "message_id": str(uuid.uuid4()),
            "conversation_id": "c1",
            "sender_agent_id": "s1",
            "recipient_agent_id": "r1",
            "payload": {},
            "timestamp": datetime.now(UTC).isoformat(),
        }
        assert not A2ASecurityService.verify_signature(payload, secret, "invalid-signature")
