import uuid

import pytest


@pytest.mark.asyncio
async def test_client_api_key_flow(e2e_client, admin_headers):
    # 1. Criar cliente
    client_payload = {"name": "E2E Client", "rate_limit_per_minute": 60}
    resp = await e2e_client.post("/admin/clients", json=client_payload, headers=admin_headers)
    assert resp.status_code == 201
    client_id = resp.json()["id"]

    # 2. Criar API key
    key_payload = {"client_id": client_id, "name": "E2E Key"}
    resp = await e2e_client.post("/admin/api-keys", json=key_payload, headers=admin_headers)
    assert resp.status_code == 201
    api_key = resp.json()["api_key"]
    client_headers = {"Authorization": f"Bearer {api_key}"}

    # 3. Registrar um backend
    backend_id = uuid.uuid4()
    backend_payload = {
        "name": "mock-backend",
        "provider": "openai_compatible",
        "backend_url": "http://localhost:8081",
        "enabled": True,
        "priority": 1,
        "metadata_json": "{}",
    }
    # Wait, check /admin/backends API
    # In admin.py: @router.post("/backends", response_model=InferenceBackendRead, status_code=201)
    resp = await e2e_client.post("/admin/backends", json=backend_payload, headers=admin_headers)
    assert resp.status_code == 201
    backend_id = resp.json()["id"]

    # 4. Registrar o modelo vinculado ao backend
    model_payload = {
        "model_id": "mock-model",
        "display_name": "Mock Model",
        "inference_backend_id": backend_id,
        "provider": "openai_compatible",
        "model_file": "mock-model.gguf",
        "is_active": True,
    }
    resp = await e2e_client.post("/admin/models", json=model_payload, headers=admin_headers)
    assert resp.status_code == 201

    # 5. Chamar /v1/models
    resp = await e2e_client.get("/v1/models", headers=client_headers)
    assert resp.status_code == 200
    models = resp.json()["data"]
    assert any(m["id"] == "mock-model" for m in models)

    # 6. Chamar /v1/chat/completions
    chat_payload = {"model": "mock-model", "messages": [{"role": "user", "content": "Hello"}]}
    resp = await e2e_client.post("/v1/chat/completions", json=chat_payload, headers=client_headers)
    assert resp.status_code == 200
    assert "choices" in resp.json()

    # 7. Validar usage_record
    # Usando export-data que sabemos que existe
    usage_resp = await e2e_client.get(
        f"/admin/clients/export-data?client_id={client_id}", headers=admin_headers
    )
    assert usage_resp.status_code == 200
    usage = usage_resp.json()["usage"]
    assert len(usage) > 0
    assert usage[0]["prompt_tokens"] > 0


@pytest.mark.asyncio
async def test_admin_api_key_delete_definitely(e2e_client, admin_headers):
    # 1. Criar cliente
    client_payload = {"name": "Delete Test Client", "rate_limit_per_minute": 60}
    resp = await e2e_client.post("/admin/clients", json=client_payload, headers=admin_headers)
    assert resp.status_code == 201
    client_id = resp.json()["id"]

    # 2. Criar API key
    key_payload = {"client_id": client_id, "name": "Delete Test Key"}
    resp = await e2e_client.post("/admin/api-keys", json=key_payload, headers=admin_headers)
    assert resp.status_code == 201
    key_id = resp.json()["id"]

    # 3. List keys to verify it's there
    resp = await e2e_client.get("/admin/api-keys", headers=admin_headers)
    assert resp.status_code == 200
    keys = resp.json()
    assert any(k["id"] == key_id for k in keys)
    key_item = next(k for k in keys if k["id"] == key_id)
    assert key_item["is_active"] is True
    assert key_item["revoked_at"] is None

    # 4. First DELETE call -> should soft-delete (revoke)
    resp = await e2e_client.delete(f"/admin/api-keys/{key_id}", headers=admin_headers)
    assert resp.status_code == 204

    # Verify it is still listed but is revoked/inactive
    resp = await e2e_client.get("/admin/api-keys", headers=admin_headers)
    assert resp.status_code == 200
    keys = resp.json()
    assert any(k["id"] == key_id for k in keys)
    key_item = next(k for k in keys if k["id"] == key_id)
    assert key_item["is_active"] is False
    assert key_item["revoked_at"] is not None

    # 5. Second DELETE call -> should hard-delete (definitely remove from DB)
    resp = await e2e_client.delete(f"/admin/api-keys/{key_id}", headers=admin_headers)
    assert resp.status_code == 204

    # Verify it is completely gone
    resp = await e2e_client.get("/admin/api-keys", headers=admin_headers)
    assert resp.status_code == 200
    keys = resp.json()
    assert not any(k["id"] == key_id for k in keys)

    # 6. Third DELETE call -> should return 404 (not found)
    resp = await e2e_client.delete(f"/admin/api-keys/{key_id}", headers=admin_headers)
    assert resp.status_code == 404
