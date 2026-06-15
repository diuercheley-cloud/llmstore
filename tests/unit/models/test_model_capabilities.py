from pathlib import Path

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_model_capabilities_admin_list(
    admin_client: AsyncClient, admin_token_headers, models_dir: Path
):
    """
    Verifica se a listagem de modelos para admin inclui capabilities.
    """
    (models_dir / "test-cap.gguf").touch()

    # Create model
    model_id = "test/capabilities-1"
    create_payload = {
        "display_name": "Test Cap Model",
        "model_id": model_id,
        "model_alias": "test-cap-model",
        "provider": "llama.cpp",
        "model_file": "test-cap.gguf",
        "is_active": True,
        "is_default": False,
        "context_length": 2048,
    }
    create_resp = await admin_client.post(
        "/admin/models", json=create_payload, headers=admin_token_headers
    )
    assert create_resp.status_code == 201
    model_uuid = create_resp.json()["id"]

    # List models
    list_resp = await admin_client.get("/admin/models", headers=admin_token_headers)
    assert list_resp.status_code == 200
    data = list_resp.json()

    # We need to find our model in registry
    found = [m for m in data["registry"] if m["id"] == model_uuid]
    assert len(found) == 1
    model = found[0]

    assert "capabilities" in model
    assert model["capabilities"]["supports_chat"] is True
    assert model["capabilities"]["supports_streaming"] is True
    assert model["capabilities"]["supports_responses"] is True
    assert model["capabilities"]["supports_tools"] is False


@pytest.mark.asyncio
async def test_model_capabilities_v1_models(
    admin_client: AsyncClient, admin_token_headers, models_dir: Path
):
    """
    Verifica se os modelos em /v1/models incluem capabilities no metadata.
    """
    (models_dir / "test-v1-cap.gguf").touch()

    # Create model
    model_id = "test/v1-capabilities-1"
    create_payload = {
        "model_id": model_id,
        "model_alias": "v1-cap-model",
        "provider": "llama.cpp",
        "model_file": "test-v1-cap.gguf",
        "is_active": True,
        "context_length": 2048,
    }
    await admin_client.post("/admin/models", json=create_payload, headers=admin_token_headers)

    # Create a client and API key to use /v1/models
    client_payload = {"name": "test-v1-cap-client"}
    client_resp = await admin_client.post(
        "/admin/clients", json=client_payload, headers=admin_token_headers
    )
    client_id = client_resp.json()["id"]

    key_payload = {"client_id": client_id, "name": "test-key"}
    key_resp = await admin_client.post(
        "/admin/api-keys", json=key_payload, headers=admin_token_headers
    )
    api_key = key_resp.json()["api_key"]

    # List via /v1/models
    v1_resp = await admin_client.get("/v1/models", headers={"Authorization": f"Bearer {api_key}"})
    assert v1_resp.status_code == 200
    data = v1_resp.json()

    found = [m for m in data["data"] if m["id"] in [model_id, "v1-cap-model"]]
    assert len(found) >= 1
    model = found[0]

    assert "capabilities" in model
    assert model["capabilities"]["chat"] is True
