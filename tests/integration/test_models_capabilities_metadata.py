import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_models_v1_includes_enhanced_metadata(admin_client: AsyncClient, admin_token_headers):
    """Verifica se /v1/models retorna os novos campos de metadados."""
    # Primeiro criar um modelo para garantir que a lista não esteja vazia
    create_payload = {
        "model_id": "test-enhanced-metadata",
        "provider": "ollama",
        "model_file": "test",
        "is_active": True,
        "context_length": 2048,
    }
    await admin_client.post("/admin/models", json=create_payload, headers=admin_token_headers)

    # Obter API Key de um cliente para usar /v1/models
    client_resp = await admin_client.post(
        "/admin/clients", json={"name": "test-client"}, headers=admin_token_headers
    )
    client_id = client_resp.json()["id"]
    key_resp = await admin_client.post(
        "/admin/api-keys",
        json={"client_id": client_id, "name": "test-key"},
        headers=admin_token_headers,
    )
    api_key = key_resp.json()["api_key"]

    resp = await admin_client.get("/v1/models", headers={"Authorization": f"Bearer {api_key}"})
    assert resp.status_code == 200
    data = resp.json()["data"]

    found = [m for m in data if m["id"] == "test-enhanced-metadata"]
    assert len(found) > 0
    model = found[0]
    assert "capabilities" in model
    assert "chat" in model["capabilities"]
    assert "streaming" in model["capabilities"]
    assert "enabled" in model
    assert "backend_status" in model
    assert "local_ready" in model
    assert "production_ready" in model


@pytest.mark.asyncio
async def test_embedding_model_capabilities(admin_client: AsyncClient, admin_token_headers):
    """Verifica se modelos de embedding têm capabilities corretas."""
    # O modelo gpt-4-embedding-mock é adicionado automaticamente se embeddings_enabled=True
    client_resp = await admin_client.post(
        "/admin/clients", json={"name": "test-client-2"}, headers=admin_token_headers
    )
    client_id = client_resp.json()["id"]
    key_resp = await admin_client.post(
        "/admin/api-keys",
        json={"client_id": client_id, "name": "test-key-2"},
        headers=admin_token_headers,
    )
    api_key = key_resp.json()["api_key"]

    resp = await admin_client.get("/v1/models", headers={"Authorization": f"Bearer {api_key}"})
    data = resp.json()["data"]

    # Encontrar modelo de embedding
    embedding_models = [m for m in data if m["capabilities"]["embeddings"] is True]
    assert len(embedding_models) > 0

    for m in embedding_models:
        assert m["capabilities"]["chat"] is False
        assert m["capabilities"]["streaming"] is False
