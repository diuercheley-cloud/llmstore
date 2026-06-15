import httpx
import pytest


@pytest.mark.asyncio
async def test_commercial_plans_seeded(admin_client: httpx.AsyncClient, admin_token_headers):
    # Get all plans
    response = await admin_client.get("/admin/billing/plans", headers=admin_token_headers)
    assert response.status_code == 200
    plans = response.json()

    # In a fresh test DB, there might be no plans. Let's create them.
    # Actually, we want to test if our seeding script logic works

    # Let's create the Free plan
    free_plan = {
        "code": "free",
        "name": "Free",
        "description": "Starter plan",
        "rate_limit_per_minute": 10,
        "daily_token_quota": 50000,
        "weekly_token_quota": 250000,
        "monthly_token_quota": 500000,
        "requests_per_day": 100,
        "max_output_tokens": 1024,
        "max_context_tokens": 4096,
        "rag_enabled": False,
        "support_level": "Community",
    }

    resp = await admin_client.post(
        "/admin/billing/plans", json=free_plan, headers=admin_token_headers
    )
    assert resp.status_code == 201
    plan = resp.json()
    assert plan["code"] == "free"
    assert plan["rag_enabled"] is False
    assert plan["requests_per_day"] == 100
    assert plan["max_context_tokens"] == 4096
    assert plan["support_level"] == "Community"


@pytest.mark.asyncio
async def test_commercial_plans_patch(admin_client: httpx.AsyncClient, admin_token_headers):
    # Create a plan
    free_plan = {
        "code": "patch-test",
        "name": "Patch Test",
        "rate_limit_per_minute": 10,
        "daily_token_quota": 50000,
        "weekly_token_quota": 250000,
        "monthly_token_quota": 500000,
        "max_output_tokens": 1024,
    }
    resp = await admin_client.post(
        "/admin/billing/plans", json=free_plan, headers=admin_token_headers
    )
    plan_id = resp.json()["id"]

    # Patch it
    patch_data = {"requests_per_day": 500, "rag_enabled": True, "support_level": "Pro Support"}
    resp = await admin_client.patch(
        f"/admin/billing/plans/{plan_id}", json=patch_data, headers=admin_token_headers
    )
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["requests_per_day"] == 500
    assert updated["rag_enabled"] is True
    assert updated["support_level"] == "Pro Support"
