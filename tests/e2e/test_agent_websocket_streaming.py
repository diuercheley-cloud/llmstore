# Owner: agent-platform
import uuid

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect


@pytest.mark.asyncio
async def test_agent_websocket_streaming_flow(e2e_client, admin_headers):
    # Import app models and configurations inside test to respect monkeypatched DB/Session
    from app.core.config import get_settings
    from app.core.security import hash_secret
    from app.db.session import SessionLocal
    from app.main import app as fastapi_app
    from app.models.agents.agents import AgentDefinition, AgentRun
    from app.models.core.api_key import ApiKey
    from app.models.core.client import Client as DBClient
    from app.services.agents.streaming.run_event_stream import RunEventStreamService

    settings = get_settings()
    client_id = uuid.uuid4()
    run_id = uuid.uuid4()
    
    # Api key parameters
    api_key_plaintext = "pk_test_1234567890abcdef1234567890"
    api_key_prefix = api_key_plaintext[:12]
    api_key_hash = hash_secret(api_key_plaintext)

    # 1. Seed database with Client, ApiKey, AgentDefinition, and AgentRun
    async with SessionLocal() as db:
        tenant_client = DBClient(
            id=client_id,
            name="WS Tenant Client",
            is_blocked=False,
            billing_status="active"
        )
        db.add(tenant_client)
        await db.flush()

        key = ApiKey(
            id=uuid.uuid4(),
            client_id=client_id,
            name="WS E2E Key",
            key_prefix=api_key_prefix,
            key_hash=api_key_hash,
            is_active=True
        )
        db.add(key)
        await db.flush()

        agent_def = AgentDefinition(
            id=uuid.uuid4(),
            name="WS Run Agent",
            version="1.0.0",
            instructions="Testing websocket run streaming",
            model_id="mock-model",
            owner="admin",
            tenant_id=str(client_id),
            status="active",
            allowed_tools=[]
        )
        db.add(agent_def)
        await db.flush()

        run = AgentRun(
            id=run_id,
            tenant_id=str(client_id),
            agent_id=agent_def.id,
            status="running",
            input_text="hello"
        )
        db.add(run)
        await db.commit()

    # Create synchronous TestClient to make WebSocket tests straightforward
    tc = TestClient(fastapi_app)

    # Step A: Assert that WebSocket is rejected when disabled
    settings.agent_websocket_streaming_enabled = False
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with tc.websocket_connect(f"/v1/agents/runs/{run_id}/stream?token={api_key_plaintext}") as ws:
            pass
    assert exc_info.value.code == 1008  # Policy violation

    # Enable flag for the rest of tests
    settings.agent_websocket_streaming_enabled = True

    # Step B: Assert that invalid auth blocks
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with tc.websocket_connect(f"/v1/agents/runs/{run_id}/stream?token=pk_live_wrong_token") as ws:
            pass
    assert exc_info.value.code == 1008

    # Step C: Assert tenant isolation blocks (different tenant api key accessing this run)
    other_client_id = uuid.uuid4()
    other_key_plaintext = "pk_test_other1234567890abcdef123"
    other_key_prefix = other_key_plaintext[:12]
    other_key_hash = hash_secret(other_key_plaintext)

    async with SessionLocal() as db:
        other_client = DBClient(
            id=other_client_id,
            name="Other WS Client",
            is_blocked=False,
            billing_status="active"
        )
        db.add(other_client)
        await db.flush()

        other_key = ApiKey(
            id=uuid.uuid4(),
            client_id=other_client_id,
            name="WS Other Key",
            key_prefix=other_key_prefix,
            key_hash=other_key_hash,
            is_active=True
        )
        db.add(other_key)
        await db.commit()

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with tc.websocket_connect(f"/v1/agents/runs/{run_id}/stream?token={other_key_plaintext}") as ws:
            pass
    assert exc_info.value.code == 1008

    # Step D: Connect successfully with valid token
    with tc.websocket_connect(f"/v1/agents/runs/{run_id}/stream?token={api_key_plaintext}") as ws:
        # Step E: Check Sanitization of Streamed Events (Redacts API keys and database password structures)
        sensitive_data = {
            "model_response": "Here is the response. Secret: fake-secret-key-32-chars-max-for-testing",
            "db_details": {
                "db_url": "postgresql://app_user:dbpassword123@localhost/prod_db",
                "non_sensitive_field": "public_data"
            }
        }
        
        # Publish run event
        await RunEventStreamService.publish_run_event(str(run_id), "model.delta", sensitive_data)

        # Receive streamed event over WebSocket
        event_msg = ws.receive_json()
        assert event_msg["event"] == "model.delta"
        assert event_msg["run_id"] == str(run_id)
        
        # Validate that sensitive data has been sanitized
        data = event_msg["data"]
        assert "fake-secret-key-32-chars-max-for-testing" not in data["model_response"]
        assert "[API_KEY_REDACTED]" in data["model_response"]
        assert data["db_details"]["db_url"] == "[DB_URL_REDACTED]"
        assert data["db_details"]["non_sensitive_field"] == "public_data"

        # Step F: Cancel run via WebSocket command
        ws.send_json({"command": "cancel"})
        resp = ws.receive_json()
        assert resp["status"] == "command_processed"
        assert resp["command"] == "cancel"
        assert resp["success"] is True

        # Assert status updated to cancelled in database
        async with SessionLocal() as db:
            updated_run = await db.get(AgentRun, run_id)
            assert updated_run.status == "cancelled"

        # Re-set status to running to test pause/resume
        async with SessionLocal() as db:
            run_obj = await db.get(AgentRun, run_id)
            run_obj.status = "running"
            await db.commit()

        # Step G: Pause run via WebSocket command
        ws.send_json({"command": "pause"})
        resp = ws.receive_json()
        assert resp["status"] == "command_processed"
        assert resp["command"] == "pause"
        assert resp["success"] is True

        # Assert status updated to paused in database
        async with SessionLocal() as db:
            updated_run = await db.get(AgentRun, run_id)
            assert updated_run.status == "paused"

        # Step H: Resume run via WebSocket command
        ws.send_json({"command": "resume"})
        resp = ws.receive_json()
        assert resp["status"] == "command_processed"
        assert resp["command"] == "resume"
        assert resp["success"] is True

        # Assert status in database - it could be running, queued, cancelled or even completed if fast
        async with SessionLocal() as db:
            updated_run = await db.get(AgentRun, run_id)
            assert updated_run.status in ("running", "queued", "cancelled", "completed")
