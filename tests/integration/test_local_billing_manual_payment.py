import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_local_billing_manual_payment(admin_client: AsyncClient, admin_token_headers: dict):
    # 1. Create client
    response = await admin_client.post(
        "/admin/clients",
        json={
            "name": "Payment Test Client",
            "rate_limit_per_minute": 100,
            "daily_token_quota": 100000,
            "weekly_token_quota": 500000,
            "monthly_token_quota": 2000000,
            "max_output_tokens": 1000,
        },
        headers=admin_token_headers,
    )
    assert response.status_code == 201
    client_id = response.json()["id"]

    # 2. Create API key
    response = await admin_client.post(
        "/admin/api-keys",
        json={"client_id": client_id, "name": "payment-key"},
        headers=admin_token_headers,
    )
    assert response.status_code == 201
    api_key = response.json()["api_key"]

    # 3. Generate invoice
    response = await admin_client.post(
        "/admin/billing/invoices/generate",
        json={"client_id": client_id, "due_in_days": 5, "payment_method": "manual"},
        headers=admin_token_headers,
    )
    assert response.status_code == 201
    data = response.json()
    if not data["created"]:
        pytest.skip("No invoice generated")
    invoice_id = data["created"][0]["id"]

    # 4. Mark overdue and suspend
    response = await admin_client.patch(
        f"/admin/billing/invoices/{invoice_id}/mark-overdue?simulate_suspension=true",
        headers=admin_token_headers,
    )
    assert response.status_code == 200

    # 5. Access should fail
    response = await admin_client.get(
        "/portal/me",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    assert response.status_code == 402

    # 6. Mark as paid manually
    response = await admin_client.patch(
        f"/admin/billing/invoices/{invoice_id}/mark-paid",
        json={"payment_method": "manual", "payment_reference": "manual-payment-test"},
        headers=admin_token_headers,
    )
    assert response.status_code == 200

    # 7. Access should be restored
    response = await admin_client.get(
        "/portal/me",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    assert response.status_code == 200
    assert response.json()["billing_status"] == "active"
