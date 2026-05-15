import hashlib
import hmac
import json

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.security import generate_api_key, hash_secret, short_prefix
from app.db.base import Base
from app.db.session import get_db_session, get_redis
from app.models.api_key import ApiKey
from app.models.client import Client


@pytest_asyncio.fixture
async def topup_app(fake_redis):
    from app.main import app as _app

    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async def override_db():
        async with session_local() as session:
            yield session

    settings = get_settings()
    previous_provider = settings.payment_provider
    previous_secret = settings.payment_webhook_secret
    previous_real_enabled = settings.payment_real_enabled
    settings.payment_provider = "mock"
    settings.payment_webhook_secret = ""
    settings.payment_real_enabled = False

    _app.dependency_overrides[get_db_session] = override_db
    _app.dependency_overrides[get_redis] = lambda: fake_redis
    yield _app, session_local
    _app.dependency_overrides.clear()
    settings.payment_provider = previous_provider
    settings.payment_webhook_secret = previous_secret
    settings.payment_real_enabled = previous_real_enabled
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
async def test_create_topup_mock(topup_app):
    app, session_local = topup_app
    async with session_local() as session:
        _client_obj, api_key = await _create_client_with_key(session, "topup-mock")

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
        resp = await client.post(
            "/portal/wallet/topups",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"amount_brl": "125.50", "idempotency_key": "topup-mock-1"},
        )

    assert resp.status_code == 201
    payload = resp.json()
    assert payload["provider"] == "mock"
    assert payload["status"] == "pending"
    assert payload["amount_brl"] == 125.5
    assert payload["external_id"].startswith("mock_topup_")
    assert "payment_data" in payload
    assert payload["payment_data"]["mode"] == "mock"


@pytest.mark.asyncio
async def test_confirm_mock_webhook_credits_wallet_once(topup_app):
    app, session_local = topup_app
    async with session_local() as session:
        _client_obj, api_key = await _create_client_with_key(session, "topup-credit")

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
        topup = await client.post(
            "/portal/wallet/topups",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"amount_brl": "50.00", "idempotency_key": "topup-credit-1"},
        )
        assert topup.status_code == 201
        topup_payload = topup.json()
        webhook_payload = {
            "external_id": topup_payload["external_id"],
            "idempotency_key": topup_payload["idempotency_key"],
            "amount_brl": "50.00",
            "status": "paid",
        }

        first = await client.post("/payments/webhooks/mock", json=webhook_payload)
        second = await client.post("/payments/webhooks/mock", json=webhook_payload)
        wallet = await client.get("/portal/wallet", headers={"Authorization": f"Bearer {api_key}"})

    assert first.status_code == 200
    assert first.json()["credited"] is True
    assert second.status_code == 200
    assert second.json()["status"] == "already_processed"
    assert wallet.status_code == 200
    wallet_payload = wallet.json()
    assert wallet_payload["balance_brl"] == 50.0
    credits = [tx for tx in wallet_payload["transactions"] if tx["type"] == "future_pix_credit"]
    assert len(credits) == 1


@pytest.mark.asyncio
async def test_webhook_invalid_signature_rejected(topup_app):
    app, session_local = topup_app
    get_settings().payment_webhook_secret = "test-webhook-secret"
    async with session_local() as session:
        _client_obj, api_key = await _create_client_with_key(session, "topup-signature")

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
        topup = await client.post(
            "/portal/wallet/topups",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"amount_brl": "25.00", "idempotency_key": "topup-signature-1"},
        )
        body = {
            "external_id": topup.json()["external_id"],
            "idempotency_key": topup.json()["idempotency_key"],
            "amount_brl": "25.00",
            "status": "paid",
        }
        resp = await client.post("/payments/webhooks/mock", json=body, headers={"X-Payment-Signature": "invalid"})

    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "invalid_payment_signature"


@pytest.mark.asyncio
async def test_webhook_valid_signature_is_accepted(topup_app):
    app, session_local = topup_app
    secret = "test-webhook-secret-valid"
    get_settings().payment_webhook_secret = secret
    async with session_local() as session:
        _client_obj, api_key = await _create_client_with_key(session, "topup-valid-signature")

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
        topup = await client.post(
            "/portal/wallet/topups",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"amount_brl": "10.00", "idempotency_key": "topup-valid-signature-1"},
        )
        body = json.dumps(
            {
                "external_id": topup.json()["external_id"],
                "idempotency_key": topup.json()["idempotency_key"],
                "amount_brl": "10.00",
                "status": "paid",
            },
            separators=(",", ":"),
        ).encode("utf-8")
        signature = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        resp = await client.post(
            "/payments/webhooks/mock",
            content=body,
            headers={"Content-Type": "application/json", "X-Payment-Signature": signature},
        )

    assert resp.status_code == 200
    assert resp.json()["credited"] is True


@pytest.mark.asyncio
async def test_client_cannot_see_other_client_topups(topup_app):
    app, session_local = topup_app
    async with session_local() as session:
        _client_a, key_a = await _create_client_with_key(session, "topup-client-a")
        _client_b, key_b = await _create_client_with_key(session, "topup-client-b")

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
        own = await client.post(
            "/portal/wallet/topups",
            headers={"Authorization": f"Bearer {key_a}"},
            json={"amount_brl": "11.00", "idempotency_key": "topup-client-a-1"},
        )
        other = await client.post(
            "/portal/wallet/topups",
            headers={"Authorization": f"Bearer {key_b}"},
            json={"amount_brl": "22.00", "idempotency_key": "topup-client-b-1"},
        )
        listed = await client.get("/portal/wallet/topups", headers={"Authorization": f"Bearer {key_a}"})

    assert own.status_code == 201
    assert other.status_code == 201
    assert listed.status_code == 200
    payload = listed.json()
    assert len(payload) == 1
    assert payload[0]["id"] == own.json()["id"]
    assert payload[0]["id"] != other.json()["id"]


@pytest.mark.asyncio
async def test_disabled_payment_provider_returns_clear_error(topup_app):
    app, session_local = topup_app
    get_settings().payment_provider = "disabled"
    async with session_local() as session:
        _client_obj, api_key = await _create_client_with_key(session, "topup-disabled")

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
        resp = await client.post(
            "/portal/wallet/topups",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"amount_brl": "15.00"},
        )
        webhook = await client.post(
            "/payments/webhooks/mock",
            json={"external_id": "mock_topup_disabled", "idempotency_key": "disabled-1", "amount_brl": "15.00", "status": "paid"},
        )

    assert resp.status_code == 503
    assert resp.json()["detail"]["code"] == "payment_provider_disabled"
    assert webhook.status_code == 503
    assert webhook.json()["detail"]["code"] == "payment_provider_disabled"


def test_payment_topup_docs_and_adapters_do_not_embed_real_psp_secrets():
    from pathlib import Path

    files = [
        Path("docs/WALLET_TOPUPS_PIX_PSP.md"),
        Path("control_plane/app/services/payment_adapters/mock.py"),
        Path("control_plane/app/services/payment_adapters/real.py"),
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in files if path.exists())
    forbidden = ["sk_live_", "pk_live_", "pix_key_secret", "access_token=", "client_secret="]
    assert not any(item in combined for item in forbidden)
