import pytest
import httpx

@pytest.mark.asyncio
async def test_portal_me_plan_fields(admin_client: httpx.AsyncClient, admin_token_headers):
    # 1. Create a plan
    plan_code = "portal-test-plan"
    plan_payload = {
        "code": plan_code,
        "name": "Portal Test Plan",
        "rate_limit_per_minute": 50,
        "daily_token_quota": 100000,
        "weekly_token_quota": 500000,
        "monthly_token_quota": 2000000,
        "max_output_tokens": 2048,
        "max_context_tokens": 8192,
        "requests_per_day": 500,
        "rag_enabled": True,
        "export_enabled": True,
        "support_level": "Premium"
    }
    resp = await admin_client.post("/admin/billing/plans", json=plan_payload, headers=admin_token_headers)
    plan_id = resp.json()["id"]
    
    # 2. Create client and key
    resp = await admin_client.post("/admin/clients", json={"name": "portal-client", "billing_plan_id": plan_id}, headers=admin_token_headers)
    client_id = resp.json()["id"]
    resp = await admin_client.post("/admin/api-keys", json={"client_id": client_id, "name": "test-key"}, headers=admin_token_headers)
    api_key = resp.json()["api_key"]
    
    # 3. Check /portal/me
    headers = {"Authorization": f"Bearer {api_key}"}
    resp = await admin_client.get("/portal/me", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    plan = data["plan"]
    
    assert plan["code"] == plan_code
    assert plan["requests_per_day"] == 500
    assert plan["max_context_tokens"] == 8192
    assert plan["rag_enabled"] is True
    assert plan["export_enabled"] is True
    assert plan["support_level"] == "Premium"

@pytest.mark.asyncio
async def test_portal_account_plan_fields(admin_client: httpx.AsyncClient, admin_token_headers):
    # Reuse client from above if possible, but let's create a quick new one
    plan_code = "account-test-plan"
    plan_payload = {
        "code": plan_code,
        "name": "Account Test Plan",
        "rate_limit_per_minute": 50,
        "daily_token_quota": 100000,
        "weekly_token_quota": 500000,
        "monthly_token_quota": 2000000,
        "max_output_tokens": 2048,
        "max_context_tokens": 8192,
        "requests_per_day": 500,
        "export_enabled": True
    }
    resp = await admin_client.post("/admin/billing/plans", json=plan_payload, headers=admin_token_headers)
    plan_id = resp.json()["id"]
    
    resp = await admin_client.post("/admin/clients", json={"name": "account-client", "billing_plan_id": plan_id}, headers=admin_token_headers)
    client_id = resp.json()["id"]
    resp = await admin_client.post("/admin/api-keys", json={"client_id": client_id, "name": "test-key"}, headers=admin_token_headers)
    api_key = resp.json()["api_key"]
    
    headers = {"Authorization": f"Bearer {api_key}"}
    resp = await admin_client.get("/portal/account", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    plan = data["plan"]
    
    assert plan["code"] == plan_code
    assert plan["requests_per_day"] == 500
    assert plan["export_enabled"] is True
