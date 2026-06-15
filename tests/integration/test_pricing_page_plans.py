import httpx
import pytest


@pytest.mark.asyncio
async def test_public_plans_fields(admin_client: httpx.AsyncClient, admin_token_headers):
    # 1. Create a plan with many features
    full_plan = {
        "code": "full-test",
        "name": "Full Test",
        "rate_limit_per_minute": 100,
        "daily_token_quota": 1000000,
        "weekly_token_quota": 5000000,
        "monthly_token_quota": 20000000,
        "max_output_tokens": 4096,
        "max_context_tokens": 32768,
        "rag_enabled": True,
        "tts_enabled": True,
        "support_level": "Ultra",
        "is_active": True,
    }
    await admin_client.post("/admin/billing/plans", json=full_plan, headers=admin_token_headers)

    # 2. Check public plans
    resp = await admin_client.get("/public/plans")
    assert resp.status_code == 200
    data = resp.json()
    plans = data["plans"]

    test_plan = next((p for p in plans if p["code"] == "full-test"), None)
    assert test_plan is not None
    assert test_plan["max_context_tokens"] == 32768
    assert test_plan["rag_enabled"] is True
    assert test_plan["tts_enabled"] is True
    assert test_plan["support_level"] == "Ultra"
