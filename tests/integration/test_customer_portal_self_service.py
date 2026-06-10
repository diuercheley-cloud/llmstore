import json
from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest
import pytest_asyncio
from app.core.security import generate_api_key, hash_secret, short_prefix
from app.core.time import utc_now
from app.db.base import Base
from app.db.session import get_db_session, get_redis
from app.models.core.api_key import ApiKey
from app.models.billing.billing_invoice import BillingInvoice
from app.models.core.client import Client
from app.models.billing.request_financial import RequestFinancial
from app.models.core.request_log import RequestLog
from app.models.commercial.sales_lead import SalesLead
from app.services.billing.wallet_service import credit_manual
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def portal_app(fake_redis):
    from app.main import app as _app

    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async def override_db():
        async with session_local() as session:
            yield session

    _app.dependency_overrides[get_db_session] = override_db
    _app.dependency_overrides[get_redis] = lambda: fake_redis
    yield _app, session_local
    _app.dependency_overrides.clear()
    await engine.dispose()


async def _create_client_with_key(session: AsyncSession, name: str) -> tuple[Client, str]:
    client = Client(name=name)
    session.add(client)
    await session.commit()
    await session.refresh(client)

    plaintext = generate_api_key()
    api_key = ApiKey(
        client_id=client.id,
        name=f"{name}-key",
        key_prefix=short_prefix(plaintext),
        key_hash=hash_secret(plaintext),
        scopes_json=json.dumps([]),
    )
    session.add(api_key)
    await session.commit()
    return client, plaintext


@pytest.mark.asyncio
async def test_portal_usage_wallet_invoices_examples_are_isolated_and_sanitized(portal_app):
    app, session_local = portal_app
    async with session_local() as session:
        client_a, key_a = await _create_client_with_key(session, "portal-a")
        client_b, _key_b = await _create_client_with_key(session, "portal-b")
        now = utc_now()

        session.add_all(
            [
                RequestLog(
                    client_id=client_a.id,
                    model="gpt-test",
                    endpoint="/v1/chat/completions",
                    prompt_tokens_estimated=120,
                    completion_tokens_estimated=30,
                    latency_ms=100,
                    http_status=200,
                    is_stream=False,
                    estimated_cost_usd=Decimal("0.01"),
                    request_summary="prompt-a-own",
                    created_at=now,
                ),
                RequestLog(
                    client_id=client_a.id,
                    model="gpt-test",
                    endpoint="/v1/chat/completions",
                    prompt_tokens_estimated=40,
                    completion_tokens_estimated=10,
                    latency_ms=90,
                    http_status=200,
                    is_stream=False,
                    estimated_cost_usd=Decimal("0.002"),
                    request_summary="prompt-a-own-2",
                    created_at=now,
                ),
                RequestLog(
                    client_id=client_b.id,
                    model="gpt-other",
                    endpoint="/v1/chat/completions",
                    prompt_tokens_estimated=999,
                    completion_tokens_estimated=1,
                    latency_ms=80,
                    http_status=200,
                    is_stream=False,
                    estimated_cost_usd=Decimal("9.99"),
                    request_summary="prompt-from-other-client",
                    created_at=now,
                ),
            ]
        )
        session.add_all(
            [
                RequestFinancial(
                    client_id=str(client_a.id),
                    provider="local",
                    model="gpt-test",
                    prompt_tokens=160,
                    completion_tokens=40,
                    total_tokens=200,
                    customer_price_brl=Decimal("12.3400"),
                    provider_cost_brl=Decimal("5.1200"),
                    gross_profit_brl=Decimal("7.2200"),
                    margin_percent=Decimal("58.5000"),
                    created_at=now,
                ),
                RequestFinancial(
                    client_id=str(client_b.id),
                    provider="local",
                    model="gpt-other",
                    prompt_tokens=999,
                    completion_tokens=1,
                    total_tokens=1000,
                    customer_price_brl=Decimal("88.8800"),
                    provider_cost_brl=Decimal("77.7700"),
                    gross_profit_brl=Decimal("11.1100"),
                    margin_percent=Decimal("12.5000"),
                    created_at=now,
                ),
            ]
        )
        invoice_a = BillingInvoice(
            client_id=client_a.id,
            status="pending",
            currency="BRL",
            period_start=date.today().replace(day=1),
            period_end=date.today(),
            monthly_price=Decimal("99.90"),
            included_tokens=1000,
            used_tokens=200,
            overage_tokens=0,
            overage_price_per_1k_tokens=Decimal("0.50"),
            overage_cost=Decimal("0.00"),
            total_amount=Decimal("99.90"),
            payment_method="manual_pix",
            payment_instructions="pagamento manual/local",
            due_at=now + timedelta(days=7),
        )
        invoice_b = BillingInvoice(
            client_id=client_b.id,
            status="overdue",
            currency="BRL",
            period_start=date.today().replace(day=1),
            period_end=date.today(),
            monthly_price=Decimal("199.90"),
            included_tokens=500,
            used_tokens=1000,
            overage_tokens=500,
            overage_price_per_1k_tokens=Decimal("1.50"),
            overage_cost=Decimal("0.75"),
            total_amount=Decimal("200.65"),
            payment_method="manual_pix",
            payment_instructions="other-client-only",
            due_at=now + timedelta(days=3),
        )
        session.add_all([invoice_a, invoice_b])
        await credit_manual(session, client_a.id, Decimal("50.00"), reason="portal seed", created_by="test")
        await credit_manual(session, client_b.id, Decimal("10.00"), reason="portal other", created_by="test")
        await session.commit()

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
        client.headers = {"Authorization": f"Bearer {key_a}"}

        usage_resp = await client.get("/portal/usage")
        assert usage_resp.status_code == 200
        usage = usage_resp.json()
        assert usage["requests_today"] == 2
        assert usage["requests_month"] == 2
        assert usage["tokens_today"] == 200
        assert usage["tokens_month"] == 200
        assert usage["customer_pricing"]["month_amount"] == 12.34
        usage_dump = json.dumps(usage)
        assert "provider_cost_brl" not in usage_dump
        assert "gross_profit_brl" not in usage_dump
        assert "margin_percent" not in usage_dump
        assert "prompt-from-other-client" not in usage_dump

        invoices_resp = await client.get("/portal/invoices")
        assert invoices_resp.status_code == 200
        invoices = invoices_resp.json()["invoices"]
        assert len(invoices) == 1
        assert invoices[0]["id"] == str(invoice_a.id)

        own_json = await client.get(f"/portal/invoices/{invoice_a.id}/download?format=json")
        assert own_json.status_code == 200
        assert own_json.json()["id"] == str(invoice_a.id)

        own_html = await client.get(f"/portal/invoices/{invoice_a.id}/download?format=html")
        assert own_html.status_code == 200
        assert "text/html" in own_html.headers["content-type"]
        assert str(invoice_a.id) in own_html.text

        other_invoice = await client.get(f"/portal/invoices/{invoice_b.id}/download?format=json")
        assert other_invoice.status_code == 404

        wallet_resp = await client.get("/portal/wallet")
        assert wallet_resp.status_code == 200
        wallet = wallet_resp.json()
        assert wallet["balance_brl"] == 50.0
        assert wallet["transactions"][0]["type"] == "manual_credit"
        wallet_dump = json.dumps(wallet)
        assert "metadata_json" not in wallet_dump
        assert "idempotency_key" not in wallet_dump
        assert str(client_b.id) not in wallet_dump

        examples_resp = await client.get("/portal/examples")
        assert examples_resp.status_code == 200
        examples = examples_resp.json()
        assert examples["base_url"].endswith("/v1")
        assert "__API_KEY__" in examples["snippets"]["curl"]
        examples_dump = json.dumps(examples)
        assert "provider_api_key" not in examples_dump


@pytest.mark.asyncio
async def test_portal_api_key_lifecycle_and_wallet_recharge_request(portal_app):
    app, session_local = portal_app
    async with session_local() as session:
        client_obj, api_key = await _create_client_with_key(session, "portal-lifecycle")

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
        client.headers = {"Authorization": f"Bearer {api_key}"}

        listed = await client.get("/portal/api-keys")
        assert listed.status_code == 200
        listed_payload = listed.json()
        assert listed_payload[0]["masked_key"].endswith("...")
        assert "api_key" not in listed_payload[0]

        created = await client.post(
            "/portal/api-keys",
            json={"client_id": str(client_obj.id), "name": "secondary-key"},
        )
        assert created.status_code == 201
        created_payload = created.json()
        new_key = created_payload["api_key"]
        new_key_id = created_payload["id"]

        probe = await client.get("/portal/me", headers={"Authorization": f"Bearer {new_key}"})
        assert probe.status_code == 200

        revoked = await client.delete(f"/portal/api-keys/{new_key_id}")
        assert revoked.status_code == 200

        revoked_probe = await client.get("/portal/me", headers={"Authorization": f"Bearer {new_key}"})
        assert revoked_probe.status_code == 401

        recharge = await client.post(
            "/portal/wallet/recharge-request",
            json={"amount_brl": 125.5, "note": "precisa de crédito para equipe"},
        )
        assert recharge.status_code == 201
        payload = recharge.json()
        assert payload["status"] == "created"

    async with session_local() as session:
        leads = (await session.execute(select(SalesLead).where(SalesLead.source == "portal_wallet_recharge"))).scalars().all()
        assert len(leads) == 1
        assert leads[0].company_name == "portal-lifecycle"
        assert "125.5" in (leads[0].notes or "")


def test_portal_html_mentions_self_service_areas():
    from pathlib import Path

    portal_path = Path("control_plane/app/static/portal/index.html")
    content = portal_path.read_text(encoding="utf-8")
    assert "Minhas Chaves de API" in content
    assert "Faturas" in content
    assert "Wallet" in content
    assert "Exemplos" in content
    assert "/v1/chat/completions" in content
