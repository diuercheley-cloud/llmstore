import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_admin_capabilities_auth(admin_client: AsyncClient):
    """
    Verifica se o endpoint /admin/capabilities exige token.
    """
    response = await admin_client.get("/admin/capabilities")
    assert response.status_code in [401, 403]

@pytest.mark.asyncio
async def test_admin_capabilities_data(admin_client: AsyncClient, admin_token_headers):
    """
    Verifica os dados retornados pelo endpoint /admin/capabilities.
    """
    response = await admin_client.get("/admin/capabilities", headers=admin_token_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    
    # Verifica campos obrigatórios no primeiro item
    item = data[0]
    assert "feature" in item
    assert "status" in item
    assert "backend_support" in item
    assert "production_ready" in item
    
    # Verifica algumas features específicas
    features = [i["feature"] for i in data]
    assert "/v1/chat/completions" in features
    assert "streaming" in features
    assert "RAG" in features
    
    # Verifica PSP/PIX real e tools conforme as regras
    psp_pix = next(i for i in data if i["feature"] == "PSP/PIX real")
    assert psp_pix["status"] == "Future"
    assert psp_pix["production_ready"] is False
    
    tools = next(i for i in data if i["feature"] == "tools/function calling")
    assert tools["status"] == "Unsupported"
    assert tools["production_ready"] is False
