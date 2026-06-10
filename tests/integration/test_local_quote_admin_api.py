import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_quote_preview_endpoint(admin_client: AsyncClient, admin_token_headers):
    payload = {
        "company_name": "API Test",
        "plan": "Pro",
        "rag": True,
        "support_hours": 2,
        "discount_percent": 5
    }
    response = await admin_client.post("/admin/sales/quote-preview", json=payload, headers=admin_token_headers)
    if response.status_code != 200:
        print(f"DEBUG Response: {response.text}")
    assert response.status_code == 200
    data = response.json()
    assert data["company_name"] == "API Test"
    assert data["plan"] == "Pro"
    assert data["totals"]["setup"] == 7500
    # Pro monthly: 2000, 2h support @ 250 -> 2500
    assert data["totals"]["recurring"] == 2500
    # Total: 10000, 5% discount -> 9500
    assert data["totals"]["first_month_final"] == 9500

@pytest.mark.asyncio
async def test_quote_preview_unauthorized(admin_client: AsyncClient):
    payload = {"company_name": "Auth Test", "plan": "Basic"}
    # No headers
    response = await admin_client.post("/admin/sales/quote-preview", json=payload)
    assert response.status_code in [401, 403]
