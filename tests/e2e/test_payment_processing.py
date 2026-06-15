# Owner: agent-platform
import json
import uuid

import pytest
from sqlalchemy import select


@pytest.mark.asyncio
async def test_payment_processing_flow(e2e_client, admin_headers, monkeypatch):
    # Import app models and configurations inside test to respect monkeypatched DB/Session
    from app.core.config import get_settings
    from app.db.session import SessionLocal
    from app.models.billing.billing_invoice import BillingInvoice
    from app.models.billing.payments import (
        PaymentAuditEvent,
        PaymentIntent,
    )
    from app.models.core.client import Client as DBClient

    settings = get_settings()
    client_id = uuid.uuid4()
    invoice_id = uuid.uuid4()
    idempotency_key = f"idem_key_{uuid.uuid4().hex[:12]}"

    # Seed client and invoice
    async with SessionLocal() as db:
        tenant_client = DBClient(
            id=client_id, name="Payment E2E Client", is_blocked=False, billing_status="active"
        )
        db.add(tenant_client)
        await db.flush()

        from datetime import date
        from decimal import Decimal

        invoice = BillingInvoice(
            id=invoice_id,
            client_id=client_id,
            status="unpaid",
            currency="brl",
            period_start=date.today(),
            period_end=date.today(),
            monthly_price=Decimal("15.00"),
            included_tokens=0,
            used_tokens=0,
            overage_tokens=0,
            overage_price_per_1k_tokens=Decimal("0"),
            overage_cost=Decimal("0"),
            total_amount=Decimal("15.00"),
        )
        db.add(invoice)
        await db.commit()

    # Step A: Assert payment disabled blocks
    settings.payment_processing_enabled = False
    resp = await e2e_client.post(
        "/admin/billing/payments/create-intent",
        json={
            "client_id": str(client_id),
            "amount_cents": 1500,
            "currency": "brl",
            "invoice_id": str(invoice_id),
            "idempotency_key": idempotency_key,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 403
    assert "Payment processing is disabled." in resp.json()["detail"]

    # Enable general payment processing
    settings.payment_processing_enabled = True

    # Step B: Create payment intent via Mock Provider (Default)
    settings.payment_provider = "mock"
    settings.stripe_payment_enabled = False

    resp = await e2e_client.post(
        "/admin/billing/payments/create-intent",
        json={
            "client_id": str(client_id),
            "amount_cents": 1500,
            "currency": "brl",
            "invoice_id": str(invoice_id),
            "idempotency_key": idempotency_key,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 200
    intent_data = resp.json()
    assert intent_data["status"] == "succeeded"
    assert intent_data["amount_cents"] == 1500
    assert intent_data["provider"] == "mock"
    assert "seti_mock_" in intent_data["client_secret"]

    intent_uuid = uuid.UUID(intent_data["id"])

    # Step C: Assert Idempotency Key Works
    # Re-sending same request should return the exact same intent instead of creating a new one
    resp_idem = await e2e_client.post(
        "/admin/billing/payments/create-intent",
        json={
            "client_id": str(client_id),
            "amount_cents": 1500,
            "currency": "brl",
            "invoice_id": str(invoice_id),
            "idempotency_key": idempotency_key,
        },
        headers=admin_headers,
    )
    assert resp_idem.status_code == 200
    assert resp_idem.json()["id"] == str(intent_uuid)

    # Step D: Verify Secret is NOT recorded in audit logs
    async with SessionLocal() as db:
        res = await db.execute(
            select(PaymentAuditEvent).where(PaymentAuditEvent.client_id == client_id)
        )
        audit_events = res.scalars().all()
        assert len(audit_events) > 0
        for event in audit_events:
            meta = event.metadata_json
            # Ensure client_secret, token, or password keys/substrings do not exist
            assert "client_secret" not in meta
            assert "secret" not in str(meta)
            assert "token" not in str(meta)

    # Step E: Stripe Disabled Blocks Stripe APIs
    settings.payment_provider = "stripe"
    settings.stripe_payment_enabled = False
    settings.stripe_secret_key = ""

    resp = await e2e_client.post(
        "/admin/billing/payments/create-intent",
        json={"client_id": str(client_id), "amount_cents": 1500, "currency": "brl"},
        headers=admin_headers,
    )
    assert resp.status_code == 403
    assert "Stripe payment is disabled." in resp.json()["detail"]

    # Enable Stripe Provider
    settings.stripe_payment_enabled = True
    settings.stripe_secret_key = "sk_test_mock_stripe_key"
    settings.stripe_webhook_secret = "whsec_mock_stripe_webhook"

    # Step F: Webhook without signature header fails immediately
    resp = await e2e_client.post(
        "/billing/webhooks/stripe",
        content=json.dumps({"id": "evt_test_1", "type": "payment_intent.succeeded"}),
        headers={},
    )
    assert resp.status_code == 400
    assert "Missing Stripe-Signature header." in resp.json()["detail"]

    # Step G: Webhook processing and verification
    # Setup mock payment intent linked to Stripe inside db for webhook consumption
    stripe_intent_id = "pi_stripe_test_12345"
    async with SessionLocal() as db:
        stripe_intent = PaymentIntent(
            id=uuid.uuid4(),
            client_id=client_id,
            invoice_id=invoice_id,
            amount_cents=1500,
            currency="brl",
            status="requires_payment_method",
            provider="stripe",
            provider_intent_id=stripe_intent_id,
            client_secret="secret_stripe_123",
            idempotency_key="stripe_idem_1",
        )
        db.add(stripe_intent)
        await db.commit()

    # Mock stripe.Webhook.construct_event to return simulated successfully verified event payload
    stripe_event_payload = {
        "id": "evt_stripe_test_abc",
        "type": "payment_intent.succeeded",
        "data": {"object": {"id": stripe_intent_id, "status": "succeeded"}},
    }

    import sys

    # Dynamically mock stripe module in sys.modules to avoid dependency issues if stripe library is missing
    class MockStripeWebhook:
        @staticmethod
        def construct_event(payload, sig, secret):
            if secret != "whsec_mock_stripe_webhook":
                raise ValueError("Wrong webhook secret")
            return stripe_event_payload

    class MockStripeModule:
        Webhook = MockStripeWebhook
        api_key = ""

    sys.modules["stripe"] = MockStripeModule()

    # Send webhook with valid signature header
    resp = await e2e_client.post(
        "/billing/webhooks/stripe",
        content=json.dumps(stripe_event_payload),
        headers={"Stripe-Signature": "t=123,v1=valid_sig"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"

    # Verify database updated status to succeeded and linked invoice updated status to paid
    async with SessionLocal() as db:
        res_intent = await db.execute(
            select(PaymentIntent).where(PaymentIntent.provider_intent_id == stripe_intent_id)
        )
        intent_obj = res_intent.scalar_one()
        assert intent_obj.status == "succeeded"

        res_inv = await db.execute(select(BillingInvoice).where(BillingInvoice.id == invoice_id))
        inv_obj = res_inv.scalar_one()
        assert inv_obj.status == "paid"

    # Step H: Webhook Duplicate is Idempotent
    # Re-sending the same webhook must skip reprocessing and return status idempotent_skip
    resp_dup = await e2e_client.post(
        "/billing/webhooks/stripe",
        content=json.dumps(stripe_event_payload),
        headers={"Stripe-Signature": "t=123,v1=valid_sig"},
    )
    assert resp_dup.status_code == 200
    assert resp_dup.json()["status"] == "idempotent_skip"

    # Step I: GET payment intent reconciles and returns
    # Switch back to mock provider for status retrieval test
    settings.payment_provider = "mock"
    settings.stripe_payment_enabled = False

    resp = await e2e_client.get(f"/admin/billing/payments/{intent_uuid}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == str(intent_uuid)
