import pytest
import json
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_lmstudio_routing_fallback(admin_client: AsyncClient, admin_token_headers):
    # Mock slot to avoid DB issues with BackendSlotManager using SessionLocal directly
    with patch("app.services.queue_manager.QueueManager.slot") as mock_slot:
        mock_slot.return_value.__aenter__.return_value = None
        
        # 1. Create a client and API key
        client_payload = {
            "name": "routing-test-client",
            "description": "testing routing",
            "daily_token_quota": 1000000
        }
        resp = await admin_client.post("/admin/clients", json=client_payload, headers=admin_token_headers)
        assert resp.status_code == 201
        client_id = resp.json()["id"]

        key_payload = {"client_id": client_id, "name": "test-key"}
        resp = await admin_client.post("/admin/api-keys", json=key_payload, headers=admin_token_headers)
        assert resp.status_code == 201
        api_key = resp.json()["api_key"]
        client_headers = {"Authorization": f"Bearer {api_key}"}

        # 2. Create a model that uses an LM Studio backend that is offline
        backend_payload = {
            "name": "lmstudio-offline",
            "provider": "openai_compatible",
            "backend_url": "http://127.0.0.1:9999/v1", # Definitely offline
            "healthcheck_path": "/v1/models",
            "is_active": True
        }
        resp = await admin_client.post("/admin/backends", json=backend_payload, headers=admin_token_headers)
        backend_id = resp.json()["id"]

        model_payload = {
            "model_id": "test-model-lmstudio",
            "display_name": "Test Model LM Studio",
            "provider": "openai_compatible",
            "model_file": "unused",
            "inference_backend_id": backend_id,
            "is_active": True
        }
        resp = await admin_client.post("/admin/models", json=model_payload, headers=admin_token_headers)
        assert resp.status_code == 201

        # 3. Try to use the model, it should fail with 503 but return backend errors
        chat_payload = {
            "model": "test-model-lmstudio",
            "messages": [{"role": "user", "content": "hi"}]
        }
        resp = await admin_client.post("/v1/chat/completions", json=chat_payload, headers=client_headers)
        assert resp.status_code == 503
        data = resp.json()
        assert "backend_errors" in data["detail"]
        assert data["detail"]["backend_errors"][0]["backend_name"] == "lmstudio-offline"
