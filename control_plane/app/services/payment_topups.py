from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import datetime
from decimal import Decimal

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.billing.payment_topup import PaymentWebhookEvent, WalletTopUpIntent
from app.models.core.client import Client
from app.services.billing.wallet_service import credit_wallet_topup
from app.services.payment_adapters import PaymentAdapterError, get_payment_adapter
from fastapi import HTTPException, Request
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

PAID_STATUSES = {"paid", "confirmed", "approved", "completed", "settled"}


def serialize_topup(intent: WalletTopUpIntent, *, include_payment_data: bool = False) -> dict:
    payload = {
        "id": str(intent.id),
        "client_id": str(intent.client_id),
        "amount_brl": float(intent.amount_brl),
        "status": intent.status,
        "provider": intent.provider,
        "external_id": intent.external_id,
        "idempotency_key": intent.idempotency_key,
        "paid_at": intent.paid_at.isoformat() if intent.paid_at else None,
        "created_at": intent.created_at.isoformat() if intent.created_at else None,
    }
    if include_payment_data:
        payload["payment_data"] = (
            json.loads(intent.payment_data_json) if intent.payment_data_json else {}
        )
    return payload


async def create_topup_intent(
    session: AsyncSession,
    *,
    client: Client,
    amount_brl: Decimal,
    idempotency_key: str | None = None,
) -> WalletTopUpIntent:
    if amount_brl <= 0:
        raise HTTPException(
            status_code=400,
            detail={"code": "invalid_topup_amount", "message": "amount_brl must be positive"},
        )

    settings = get_settings()
    provider = (settings.payment_provider or "disabled").strip().lower()
    idempotency_key = idempotency_key or f"topup_{client.id}_{uuid.uuid4().hex}"

    existing = (
        await session.execute(
            select(WalletTopUpIntent).where(
                WalletTopUpIntent.client_id == client.id,
                WalletTopUpIntent.provider == provider,
                WalletTopUpIntent.idempotency_key == idempotency_key,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    adapter = _adapter_or_http_error(provider)
    result = await adapter.create_topup_intent(
        client_id=client.id,
        amount_brl=amount_brl,
        idempotency_key=idempotency_key,
    )
    intent = WalletTopUpIntent(
        client_id=client.id,
        amount_brl=amount_brl,
        status=result.status,
        provider=result.provider,
        external_id=result.external_id,
        idempotency_key=result.idempotency_key,
        payment_data_json=json.dumps(
            _sanitize_payment_data(result.payment_data), ensure_ascii=True
        ),
    )
    session.add(intent)
    await session.flush()
    return intent


async def list_topup_intents(
    session: AsyncSession,
    *,
    client_id,
    limit: int = 50,
) -> list[WalletTopUpIntent]:
    rows = await session.execute(
        select(WalletTopUpIntent)
        .where(WalletTopUpIntent.client_id == client_id)
        .order_by(WalletTopUpIntent.created_at.desc())
        .limit(limit)
    )
    return list(rows.scalars().all())


async def process_payment_webhook(
    session: AsyncSession,
    *,
    provider: str,
    request: Request,
) -> dict:
    provider = provider.strip().lower()
    configured_provider = (get_settings().payment_provider or "disabled").strip().lower()
    if configured_provider == "disabled":
        raise HTTPException(
            status_code=503,
            detail={"code": "payment_provider_disabled", "message": "payment provider is disabled"},
        )
    if configured_provider != provider:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "payment_provider_mismatch",
                "message": "webhook provider is not configured",
            },
        )
    body = await request.body()
    _validate_webhook_signature(body, request)
    try:
        raw_payload = json.loads(body.decode("utf-8")) if body else {}
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": "invalid_webhook_json", "message": "invalid JSON payload"},
        ) from exc
    if not isinstance(raw_payload, dict):
        raise HTTPException(
            status_code=400,
            detail={"code": "invalid_webhook_payload", "message": "payload must be an object"},
        )

    adapter = _adapter_or_http_error(provider)
    try:
        webhook = adapter.parse_webhook(raw_payload)
    except PaymentAdapterError as exc:
        raise HTTPException(
            status_code=400, detail={"code": exc.code, "message": str(exc)}
        ) from exc

    existing_event = await _find_existing_webhook_event(
        session,
        provider=provider,
        external_id=webhook.external_id,
        idempotency_key=webhook.idempotency_key,
    )
    if existing_event is not None:
        return {"status": "already_processed", "event_id": str(existing_event.id)}

    intent = await _find_topup_intent(
        session,
        provider=provider,
        external_id=webhook.external_id,
        idempotency_key=webhook.idempotency_key,
    )
    if intent is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "topup_intent_not_found", "message": "topup intent not found"},
        )

    paid_at = (
        _parse_paid_at(webhook.paid_at) or utc_now() if webhook.status in PAID_STATUSES else None
    )
    event = PaymentWebhookEvent(
        client_id=intent.client_id,
        topup_intent_id=intent.id,
        amount_brl=webhook.amount_brl,
        status=webhook.status,
        provider=provider,
        external_id=webhook.external_id,
        idempotency_key=webhook.idempotency_key,
        payload_summary_json=json.dumps(_webhook_payload_summary(raw_payload), ensure_ascii=True),
        paid_at=paid_at,
    )
    session.add(event)

    credited = False
    if webhook.status in PAID_STATUSES:
        if webhook.amount_brl != intent.amount_brl:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "topup_amount_mismatch",
                    "message": "webhook amount does not match topup intent",
                },
            )
        intent.status = "paid"
        intent.paid_at = paid_at or utc_now()
        intent.updated_at = utc_now()
        await credit_wallet_topup(
            session,
            intent.client_id,
            intent.amount_brl,
            provider=provider,
            external_id=webhook.external_id,
            idempotency_key=f"wallet_topup:{provider}:{webhook.idempotency_key}",
        )
        credited = True
    else:
        intent.status = webhook.status
        intent.updated_at = utc_now()

    await session.flush()
    return {
        "status": "processed",
        "event_id": str(event.id),
        "topup_id": str(intent.id),
        "credited": credited,
    }


def _adapter_or_http_error(provider: str):
    try:
        return get_payment_adapter(provider)
    except PaymentAdapterError as exc:
        raise HTTPException(
            status_code=503, detail={"code": exc.code, "message": str(exc)}
        ) from exc


async def _find_existing_webhook_event(
    session: AsyncSession,
    *,
    provider: str,
    external_id: str | None,
    idempotency_key: str,
) -> PaymentWebhookEvent | None:
    clauses = [
        PaymentWebhookEvent.provider == provider,
        PaymentWebhookEvent.idempotency_key == idempotency_key,
    ]
    if external_id:
        clauses = [
            PaymentWebhookEvent.provider == provider,
            or_(
                PaymentWebhookEvent.external_id == external_id,
                PaymentWebhookEvent.idempotency_key == idempotency_key,
            ),
        ]
    return (await session.execute(select(PaymentWebhookEvent).where(*clauses))).scalar_one_or_none()


async def _find_topup_intent(
    session: AsyncSession,
    *,
    provider: str,
    external_id: str | None,
    idempotency_key: str,
) -> WalletTopUpIntent | None:
    if external_id:
        return (
            await session.execute(
                select(WalletTopUpIntent).where(
                    WalletTopUpIntent.provider == provider,
                    or_(
                        WalletTopUpIntent.external_id == external_id,
                        WalletTopUpIntent.idempotency_key == idempotency_key,
                    ),
                )
            )
        ).scalar_one_or_none()
    return (
        await session.execute(
            select(WalletTopUpIntent).where(
                WalletTopUpIntent.provider == provider,
                WalletTopUpIntent.idempotency_key == idempotency_key,
            )
        )
    ).scalar_one_or_none()


def _validate_webhook_signature(body: bytes, request: Request) -> None:
    secret = get_settings().payment_webhook_secret
    if not secret:
        return
    signature = request.headers.get("X-Payment-Signature", "")
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(
            status_code=401,
            detail={
                "code": "invalid_payment_signature",
                "message": "invalid payment webhook signature",
            },
        )


def _sanitize_payment_data(payment_data: dict) -> dict:
    allowed = {"mode", "pix_copy_paste", "qr_code_text", "expires_in_seconds", "checkout_url"}
    return {key: value for key, value in payment_data.items() if key in allowed}


def _webhook_payload_summary(payload: dict) -> dict:
    return {
        "keys": sorted(str(key) for key in payload),
        "status": payload.get("status"),
        "external_id": payload.get("external_id") or payload.get("payment_id") or payload.get("id"),
    }


def _parse_paid_at(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
