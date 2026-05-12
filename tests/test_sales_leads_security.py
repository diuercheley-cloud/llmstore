import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_sales_endpoints_no_auth(admin_client: AsyncClient):
    endpoints = [
        ("GET", "/admin/sales/leads"),
        ("POST", "/admin/sales/leads"),
        ("GET", "/admin/sales/leads/00000000-0000-0000-0000-000000000000"),
        ("PATCH", "/admin/sales/leads/00000000-0000-0000-0000-000000000000"),
        ("DELETE", "/admin/sales/leads/00000000-0000-0000-0000-000000000000"),
        ("POST", "/admin/sales/leads/00000000-0000-0000-0000-000000000000/notes"),
        ("POST", "/admin/sales/leads/00000000-0000-0000-0000-000000000000/advance-stage"),
    ]
    
    for method, url in endpoints:
        if method == "GET":
            response = await admin_client.get(url)
        elif method == "POST":
            response = await admin_client.post(url, json={})
        elif method == "PATCH":
            response = await admin_client.patch(url, json={})
        elif method == "DELETE":
            response = await admin_client.delete(url)
        
        assert response.status_code == 401, f"Endpoint {method} {url} should require auth"

@pytest.mark.asyncio
async def test_sales_endpoints_invalid_token(admin_client: AsyncClient):
    headers = {"X-Admin-Token": "invalid-token"}
    response = await admin_client.get("/admin/sales/leads", headers=headers)
    assert response.status_code == 401
