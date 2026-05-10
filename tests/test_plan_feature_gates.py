import pytest
import httpx
import json

@pytest.mark.asyncio
async def test_feature_gates_rag(admin_client: httpx.AsyncClient, admin_token_headers):
    # 1. Create a plan with RAG DISABLED
    free_plan = {
        "code": "free-no-rag",
        "name": "Free No RAG",
        "rate_limit_per_minute": 10,
        "daily_token_quota": 50000,
        "weekly_token_quota": 250000,
        "monthly_token_quota": 500000,
        "max_output_tokens": 1024,
        "rag_enabled": False
    }
    resp = await admin_client.post("/admin/billing/plans", json=free_plan, headers=admin_token_headers)
    assert resp.status_code == 201
    plan_id = resp.json()["id"]
    
    # 2. Create a client with this plan
    client_payload = {
        "name": "no-rag-client",
        "billing_plan_id": plan_id
    }
    resp = await admin_client.post("/admin/clients", json=client_payload, headers=admin_token_headers)
    assert resp.status_code == 201
    client_data = resp.json()
    
    # 3. Create an API key for this client
    key_payload = {
        "client_id": client_data["id"],
        "name": "test-key"
    }
    resp = await admin_client.post("/admin/api-keys", json=key_payload, headers=admin_token_headers)
    api_key = resp.json()["api_key"]
    
    # 4. Try to use RAG with this client
    headers = {"Authorization": f"Bearer {api_key}"}
    resp = await admin_client.get("/client/rag/usage", headers=headers)
    assert resp.status_code == 403
    assert "RAG feature is not enabled for your plan" in resp.text

@pytest.mark.asyncio
async def test_feature_gates_responses(admin_client: httpx.AsyncClient, admin_token_headers):
    # 1. Create a plan with RESPONSES DISABLED
    no_resp_plan = {
        "code": "no-resp",
        "name": "No Responses",
        "rate_limit_per_minute": 10,
        "daily_token_quota": 50000,
        "weekly_token_quota": 250000,
        "monthly_token_quota": 500000,
        "max_output_tokens": 1024,
        "responses_enabled": False
    }
    resp = await admin_client.post("/admin/billing/plans", json=no_resp_plan, headers=admin_token_headers)
    plan_id = resp.json()["id"]
    
    # 2. Create client and key
    resp = await admin_client.post("/admin/clients", json={"name": "no-resp-client", "billing_plan_id": plan_id}, headers=admin_token_headers)
    client_id = resp.json()["id"]
    resp = await admin_client.post("/admin/api-keys", json={"client_id": client_id, "name": "test-key"}, headers=admin_token_headers)
    api_key = resp.json()["api_key"]
    
    # 3. Try to use /v1/responses
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {
        "model": "any",
        "input": "test"
    }
    resp = await admin_client.post("/v1/responses", json=payload, headers=headers)
    assert resp.status_code == 403
    assert "responses feature is not enabled for your plan" in resp.text

@pytest.mark.asyncio
async def test_request_day_limit(admin_client: httpx.AsyncClient, admin_token_headers):
    # 1. Create a plan with 1 Request Per Day
    limit_plan = {
        "code": "one-req",
        "name": "One Req",
        "rate_limit_per_minute": 10,
        "daily_token_quota": 50000,
        "weekly_token_quota": 250000,
        "monthly_token_quota": 500000,
        "max_output_tokens": 1024,
        "requests_per_day": 1
    }
    resp = await admin_client.post("/admin/billing/plans", json=limit_plan, headers=admin_token_headers)
    plan_id = resp.json()["id"]
    
    # 2. Create client and key
    resp = await admin_client.post("/admin/clients", json={"name": "limit-client", "billing_plan_id": plan_id}, headers=admin_token_headers)
    client_id = resp.json()["id"]
    resp = await admin_client.post("/admin/api-keys", json={"client_id": client_id, "name": "test-key"}, headers=admin_token_headers)
    api_key = resp.json()["api_key"]
    
    # 3. Check that it passes on first request (quota not exceeded)
    headers = {"Authorization": f"Bearer {api_key}"}
    chat_payload = {
        "model": "default",
        "messages": [{"role": "user", "content": "hi"}]
    }
    
    resp = await admin_client.post("/v1/chat/completions", json=chat_payload, headers=headers)
    # It might be 503 if no backend, but not 429
    assert resp.status_code != 429
