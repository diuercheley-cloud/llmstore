# Owner: agent-platform
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select


@pytest.mark.asyncio
async def test_agent_a2a_protocol_flow(e2e_client, admin_headers):
    from app.core.config import get_settings
    from app.db.session import SessionLocal
    from app.models.admin_rbac import AdminAuditEvent
    from app.models.agents import AgentDefinition, AgentDelegationPolicy
    from app.services.agents.a2a.a2a_client import A2AClientService
    from app.services.agents.a2a.a2a_security import A2ASecurityService

    # 1. Access settings
    settings = get_settings()

    # Create distinct UUIDs and tenant ID for our tests
    tenant_id = "tenant-a2a-e2e"
    sender_id = uuid.uuid4()
    receiver_id = uuid.uuid4()
    external_agent_id = uuid.uuid4()

    # Step A: Assert that A2A starts disabled (Feature flags are disabled by default)
    settings.agent_a2a_enabled = False
    settings.agent_a2a_external_enabled = False

    # Attempt to list agents - must fail with 403
    resp = await e2e_client.get(f"/admin/agents/a2a/agents?tenant_id={tenant_id}", headers=admin_headers)
    assert resp.status_code == 403
    assert "Agentic A2A Protocol is disabled." in resp.json()["detail"]

    # Attempt to register - must fail with 403
    reg_payload = {
        "tenant_id": tenant_id,
        "agent_id": str(sender_id),
        "auth_token": "token-sender",
        "is_external": False
    }
    resp = await e2e_client.post("/admin/agents/a2a/register", json=reg_payload, headers=admin_headers)
    assert resp.status_code == 403

    # Step B: Turn on A2A but keep External A2A disabled
    settings.agent_a2a_enabled = True
    settings.agent_a2a_external_enabled = False

    # Registering an external agent must be blocked
    ext_reg_payload = {
        "tenant_id": tenant_id,
        "agent_id": str(external_agent_id),
        "auth_token": "token-external",
        "is_external": True,
        "agent_name": "External Test Agent"
    }
    resp = await e2e_client.post("/admin/agents/a2a/register", json=ext_reg_payload, headers=admin_headers)
    assert resp.status_code == 403
    assert "External Agentic A2A is disabled." in resp.json()["detail"]

    # Enable External A2A
    settings.agent_a2a_external_enabled = True

    # Step C: Prepare internal agent definitions in database
    async with SessionLocal() as db:
        sender_def = AgentDefinition(
            id=sender_id,
            name="A2A Sender Agent",
            version="1.0.0",
            instructions="E2E testing A2A sender",
            model_id="mock-model",
            owner="admin",
            tenant_id=tenant_id,
            status="active",
            allowed_tools=[]
        )
        receiver_def = AgentDefinition(
            id=receiver_id,
            name="A2A Receiver Agent",
            version="1.0.0",
            instructions="E2E testing A2A receiver",
            model_id="mock-model",
            owner="admin",
            tenant_id=tenant_id,
            status="active",
            allowed_tools=[]
        )
        db.add(sender_def)
        db.add(receiver_def)
        await db.commit()

    # Step D: Register the internal agents via Admin API
    # 1. Register sender
    resp = await e2e_client.post("/admin/agents/a2a/register", json={
        "tenant_id": tenant_id,
        "agent_id": str(sender_id),
        "auth_token": "token-sender",
        "capabilities": {"features": ["messaging"]},
        "is_external": False
    }, headers=admin_headers)
    assert resp.status_code == 200
    sender_reg_data = resp.json()
    assert sender_reg_data["agent_id"] == str(sender_id)

    # 2. Register receiver
    resp = await e2e_client.post("/admin/agents/a2a/register", json={
        "tenant_id": tenant_id,
        "agent_id": str(receiver_id),
        "auth_token": "token-receiver",
        "capabilities": {"features": ["delegation"]},
        "is_external": False
    }, headers=admin_headers)
    assert resp.status_code == 200

    # 3. Register external agent (this should create a placeholder definition automatically)
    resp = await e2e_client.post("/admin/agents/a2a/register", json={
        "tenant_id": tenant_id,
        "agent_id": str(external_agent_id),
        "auth_token": "token-external",
        "capabilities": {"features": ["translation"]},
        "is_external": True,
        "agent_name": "External Translator"
    }, headers=admin_headers)
    assert resp.status_code == 200

    # Verify placeholder external agent definition exists
    async with SessionLocal() as db:
        res = await db.execute(select(AgentDefinition).where(AgentDefinition.id == external_agent_id))
        ext_def = res.scalar_one_or_none()
        assert ext_def is not None
        assert ext_def.owner == "external"

    # Step E: Capability Discovery
    resp = await e2e_client.get(f"/admin/agents/a2a/agents?tenant_id={tenant_id}", headers=admin_headers)
    assert resp.status_code == 200
    agents_list = resp.json()
    assert len(agents_list) == 3
    # Check that external agent capability translation is listed
    ext_agent = next(a for a in agents_list if a["agent_id"] == str(external_agent_id))
    assert ext_agent["capabilities"]["features"] == ["translation"]

    # Step F: Cross-Tenant Protection
    # Trying to register receiver agent under a different tenant must block
    resp = await e2e_client.post("/admin/agents/a2a/register", json={
        "tenant_id": "tenant-other",
        "agent_id": str(receiver_id),
        "auth_token": "token-receiver-other",
        "is_external": False
    }, headers=admin_headers)
    assert resp.status_code == 403
    assert "Cross-tenant registration is blocked." in resp.json()["detail"]

    # Step G: Send/Receive Messages (HMAC-SHA256 signature verification)
    conversation_id = "conv-e2e-1"
    msg_payload = {
        "message_id": str(uuid.uuid4()),
        "conversation_id": conversation_id,
        "sender_agent_id": str(sender_id),
        "recipient_agent_id": str(receiver_id),
        "content_type": "text/plain",
        "payload": {"text": "Hello, receiver!"},
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # 1. Sign signature
    signature = A2ASecurityService.generate_signature(msg_payload, "token-sender")
    msg_payload["signature"] = signature

    # 2. Try sending message without valid token in header
    resp = await e2e_client.post(
        "/agents/a2a/message",
        json=msg_payload,
        headers={"X-Agent-A2A-Token": "token-wrong"}
    )
    assert resp.status_code == 401
    assert "Invalid A2A authentication token." in resp.json()["detail"]

    # 3. Try sending message with wrong signature
    wrong_payload = msg_payload.copy()
    wrong_payload["signature"] = "wrong-sig"
    resp = await e2e_client.post(
        "/agents/a2a/message",
        json=wrong_payload,
        headers={"X-Agent-A2A-Token": "token-sender"}
    )
    assert resp.status_code == 400
    assert "Invalid message signature." in resp.json()["detail"]

    # 4. Successful message delivery
    resp = await e2e_client.post(
        "/agents/a2a/message",
        json=msg_payload,
        headers={"X-Agent-A2A-Token": "token-sender"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"

    # Step H: Task Delegation requires policy check
    task_id = str(uuid.uuid4())
    delegation_payload = {
        "task_id": task_id,
        "delegator_agent_id": str(sender_id),
        "delegatee_agent_id": str(receiver_id),
        "task_description": "Translate this text.",
        "input_data": {"text": "hello"},
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    delegation_signature = A2ASecurityService.generate_signature(delegation_payload, "token-sender")
    delegation_payload["signature"] = delegation_signature

    # 1. Delegate without policy - must fail with 403
    resp = await e2e_client.post(
        "/agents/a2a/delegate",
        json=delegation_payload,
        headers={"X-Agent-A2A-Token": "token-sender"}
    )
    assert resp.status_code == 403
    assert "Delegation policy" in resp.json()["detail"]

    # 2. Add an active AgentDelegationPolicy
    async with SessionLocal() as db:
        policy = AgentDelegationPolicy(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            source_agent_id=sender_id,
            target_agent_id=receiver_id,
            is_active=True
        )
        db.add(policy)
        await db.commit()

    # 3. Delegate with active policy - must succeed
    resp = await e2e_client.post(
        "/agents/a2a/delegate",
        json=delegation_payload,
        headers={"X-Agent-A2A-Token": "token-sender"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"

    # Step I: Verify Audit Event generation
    async with SessionLocal() as db:
        res = await db.execute(select(AdminAuditEvent).order_by(AdminAuditEvent.created_at.desc()))
        events = res.scalars().all()
        # Verify message receipt audit event was logged
        msg_received_event = next(e for e in events if e.event_type == "agent.a2a.message.received")
        assert msg_received_event.status == "success"
        assert msg_received_event.target_id == str(receiver_id)

        # Verify delegation receipt audit event was logged
        del_received_event = next(e for e in events if e.event_type == "agent.a2a.delegation.received")
        assert del_received_event.status == "success"
        assert del_received_event.target_id == str(receiver_id)

    # Step J: Client SDK Service flow validation
    # Verify that the service itself runs outgoing flow correctly
    async with SessionLocal() as db:
        client_msg_resp = await A2AClientService.send_message(
            db=db,
            tenant_id=tenant_id,
            sender_agent_id=sender_id,
            recipient_agent_id=receiver_id,
            conversation_id=conversation_id,
            content_type="text/plain",
            payload_data={"client": "sdk-message"}
        )
        assert client_msg_resp["status"] == "delivered_locally"

        client_del_resp = await A2AClientService.delegate_task(
            db=db,
            tenant_id=tenant_id,
            delegator_agent_id=sender_id,
            delegatee_agent_id=receiver_id,
            task_description="Client task delegation",
            input_data={"client": "sdk-delegate"}
        )
        assert client_del_resp["status"] == "delegated_locally"

        # Verify sent audit events
        res = await db.execute(select(AdminAuditEvent).order_by(AdminAuditEvent.created_at.desc()))
        updated_events = res.scalars().all()
        sent_msg_event = next(e for e in updated_events if e.event_type == "agent.a2a.message.sent")
        assert sent_msg_event.status == "success"
        assert sent_msg_event.target_id == str(receiver_id)
