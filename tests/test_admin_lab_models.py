import pytest
from httpx import AsyncClient
from pathlib import Path

@pytest.mark.asyncio
async def test_list_models_empty(admin_client: AsyncClient, admin_token_headers):
    response = await admin_client.get("/admin/models", headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert "registry" in data
    assert "backends" in data
    assert "plan_access" in data

@pytest.mark.asyncio
async def test_create_and_list_model(admin_client: AsyncClient, admin_token_headers, models_dir: Path):
    (models_dir / "test.gguf").touch()
    
    # Create model
    model_id = "test/model-1"
    create_payload = {
        "display_name": "Test Model",
        "model_id": model_id,
        "model_alias": "test-model",
        "provider": "llama.cpp",
        "model_file": "test.gguf",
        "is_active": True,
        "is_default": False,
        "context_length": 2048
    }
    create_resp = await admin_client.post("/admin/models", json=create_payload, headers=admin_token_headers)
    assert create_resp.status_code == 201
    model_uuid = create_resp.json()["id"]

    # List
    list_resp = await admin_client.get("/admin/models", headers=admin_token_headers)
    assert list_resp.status_code == 200
    data = list_resp.json()
    found = [m for m in data["registry"] if m["id"] == model_uuid]
    assert len(found) == 1
    assert found[0]["model_id"] == model_id

@pytest.mark.asyncio
async def test_model_enable_disable(admin_client: AsyncClient, admin_token_headers, models_dir: Path):
    (models_dir / "test.gguf").touch()
    
    # Create
    model_id = "test/model-toggle"
    create_payload = {
        "model_id": model_id,
        "provider": "llama.cpp",
        "model_file": "test.gguf",
        "is_active": False
    }
    create_resp = await admin_client.post("/admin/models", json=create_payload, headers=admin_token_headers)
    assert create_resp.status_code == 201
    model_uuid = create_resp.json()["id"]

    # Enable
    resp = await admin_client.post(f"/admin/models/{model_uuid}/enable", headers=admin_token_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "enabled"

    # Verify
    list_resp = await admin_client.get("/admin/models", headers=admin_token_headers)
    found = [m for m in list_resp.json()["registry"] if m["id"] == model_uuid]
    assert found[0]["is_active"] is True

    # Disable
    resp = await admin_client.post(f"/admin/models/{model_uuid}/disable", headers=admin_token_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "disabled"

    # Verify
    list_resp = await admin_client.get("/admin/models", headers=admin_token_headers)
    found = [m for m in list_resp.json()["registry"] if m["id"] == model_uuid]
    assert found[0]["is_active"] is False

@pytest.mark.asyncio
async def test_remove_model(admin_client: AsyncClient, admin_token_headers, models_dir: Path):
    (models_dir / "test.gguf").touch()
    
    # Create
    model_id = "test/model-remove"
    create_payload = {
        "model_id": model_id,
        "provider": "llama.cpp",
        "model_file": "test.gguf",
        "is_active": True
    }
    create_resp = await admin_client.post("/admin/models", json=create_payload, headers=admin_token_headers)
    assert create_resp.status_code == 201
    model_uuid = create_resp.json()["id"]

    # Remove
    remove_payload = {"confirm_route_removal": True, "mode": "hard"}
    resp = await admin_client.request("DELETE", f"/admin/models/{model_uuid}", json=remove_payload, headers=admin_token_headers)
    assert resp.status_code == 200
    
    # Verify
    list_resp = await admin_client.get("/admin/models", headers=admin_token_headers)
    found = [m for m in list_resp.json()["registry"] if m["id"] == model_uuid]
    assert len(found) == 0
