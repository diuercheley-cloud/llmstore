from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.time import utc_now
from app.db.session import get_db_session
from app.models.billing_invoice import BillingInvoice
from app.models.customer_payment import CustomerPayment
from app.schemas.public import PublicSignupRequest, PublicSignupResponse, WebhookPayload
from app.services.billing import refresh_billing_statuses
from app.services.public_onboarding import create_public_signup, list_public_plans

router = APIRouter(tags=["public"])
settings = get_settings()
static_dir = Path(__file__).resolve().parents[1] / "static" / "www"


def _base_url(request: Request) -> str:
    if settings.public_base_url:
        return settings.public_base_url.rstrip("/")
    return str(request.base_url).rstrip("/")


@router.get("/", include_in_schema=False)
async def landing_page():
    return FileResponse(static_dir / "index.html")


@router.get("/pricing", include_in_schema=False)
async def pricing_page():
    return FileResponse(static_dir / "pricing.html")


@router.get("/signup", include_in_schema=False)
async def signup_page():
    return FileResponse(static_dir / "signup.html")


@router.get("/docs", include_in_schema=False)
async def docs_page():
    return FileResponse(static_dir / "docs.html")


@router.get("/getting-started", include_in_schema=False)
async def getting_started_page():
    return FileResponse(static_dir / "getting-started.html")


@router.get("/public/plans")
async def public_plans(session: AsyncSession = Depends(get_db_session)):
    return {"brand_name": settings.public_brand_name, "plans": await list_public_plans(session)}


@router.post("/public/signup", response_model=PublicSignupResponse, status_code=201)
async def public_signup(
    payload: PublicSignupRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    if not settings.public_signup_enabled:
        raise HTTPException(status_code=404, detail="public signup disabled")
    client, plan, api_key, plaintext = await create_public_signup(session, payload)
    base_url = _base_url(request)
    return PublicSignupResponse(
        client_id=str(client.id),
        account_name=client.name,
        plan_code=plan.code,
        plan_name=plan.name,
        api_key=plaintext,
        api_key_prefix=api_key.key_prefix,
        portal_url=f"{base_url}/client-portal",
        api_base_url=f"{base_url}/v1",
        support_email=settings.public_support_email,
        next_steps=[
            "Open the client portal with the API key returned in this response.",
            "Call /v1/models to confirm access and list enabled models.",
            "Store the API key now. It is only returned once.",
        ],
    )


@router.post("/public/webhooks/local-payment", status_code=200)
async def local_payment_webhook(
    payload: WebhookPayload,
    session: AsyncSession = Depends(get_db_session),
):
    try:
        invoice_uuid = UUID(payload.invoice_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid invoice_id format")

    invoice = (
        await session.execute(
            select(BillingInvoice)
            .options(selectinload(BillingInvoice.payments))
            .where(BillingInvoice.id == invoice_uuid)
        )
    ).scalar_one_or_none()

    if not invoice:
        raise HTTPException(status_code=404, detail="invoice not found")

    if invoice.status == "paid":
        return {"status": "already_paid"}

    if payload.status == "paid":
        current_time = utc_now()
        invoice.status = "paid"
        invoice.paid_at = current_time
        invoice.updated_at = current_time

        pending_payment = next((p for p in invoice.payments if p.status in {"pending", "overdue"}), None)
        if pending_payment:
            pending_payment.status = "paid"
            pending_payment.payment_reference = payload.payment_reference or "local_payment_webhook"
            pending_payment.paid_at = current_time
            pending_payment.updated_at = current_time
        else:
            session.add(
                CustomerPayment(
                    invoice_id=invoice.id,
                    client_id=invoice.client_id,
                    status="paid",
                    amount=invoice.total_amount,
                    currency=invoice.currency,
                    payment_method=invoice.payment_method,
                    payment_reference=payload.payment_reference or "local_payment_webhook",
                    paid_at=current_time,
                )
            )

        # Trigger unsuspend logic if applicable
        await refresh_billing_statuses(session, suspend_after_days=settings.billing_suspend_after_days)
        await session.commit()
        return {"status": "paid_successfully"}

    return {"status": "ignored"}
