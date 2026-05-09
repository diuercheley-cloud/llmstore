import pytest
import pytest_asyncio
from httpx import AsyncClient

@pytest_asyncio.fixture
async def client_api_key(admin_client: AsyncClient, admin_token_headers):
    # Create a client
    resp = await admin_client.post(
        "/admin/clients",
        headers=admin_token_headers,
        json={"name": "Embedding Test Client", "rate_limit_per_minute": 100}
    )
    client_id = resp.json()["id"]
    
    # Create an API key
    resp = await admin_client.post(
        "/admin/api-keys",
        headers=admin_token_headers,
        json={"client_id": client_id, "name": "Test Key"}
    )
    return resp.json()["api_key"]

@pytest.mark.asyncio
async def test_embeddings_endpoint_basic(admin_client: AsyncClient, client_api_key: str):
    """
    Testa o endpoint /v1/embeddings básico.
    """
    response = await admin_client.post(
        "/v1/embeddings",
        headers={"Authorization": f"Bearer {client_api_key}"},
        json={
            "model": "text-embedding-3-small",
            "input": "This is a test."
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["object"] == "list"
    assert len(data["data"]) == 1
    assert data["data"][0]["object"] == "embedding"
    assert "embedding" in data["data"][0]
    assert data["model"] == "text-embedding-3-small"
    assert "usage" in data

@pytest.mark.asyncio
async def test_embeddings_array_input(admin_client: AsyncClient, client_api_key: str):
    """
    Testa o endpoint /v1/embeddings com array de strings.
    """
    response = await admin_client.post(
        "/v1/embeddings",
        headers={"Authorization": f"Bearer {client_api_key}"},
        json={
            "model": "text-embedding-3-small",
            "input": ["First", "Second"]
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 2
    assert data["data"][0]["index"] == 0
    assert data["data"][1]["index"] == 1

@pytest.mark.asyncio
async def test_embeddings_auth_required(admin_client: AsyncClient):
    """
    Testa que autenticação é obrigatória.
    """
    response = await admin_client.post(
        "/v1/embeddings",
        json={
            "model": "text-embedding-3-small",
            "input": "test"
        }
    )
    assert response.status_code == 401
