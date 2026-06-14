import json
import uuid
from datetime import date, datetime
from decimal import Decimal

from app.core.config import get_settings
from app.api.admin_usage import get_usage_summary
from app.api.deps import get_inference_proxy
from app.core.time import utc_now
from app.services.runtime_dependencies import get_db_session
from app.models.billing import BillingInvoice
from app.models.billing.billing_plan import BillingPlan
from app.models.core.client import Client
from app.models.billing.customer_payment import CustomerPayment
from app.models.billing.pricing_rule import PricingRule
from app.models.core.security_event import SecurityEvent
from app.schemas.admin import (
    BillingPlanCreate, BillingPlanPatch, BillingPlanModelsPatch,
    BillingPlanRead, ClientBillingPlanPatch, ClientRead,
    InvoiceGenerateRequest, InvoiceMarkPaidRequest,
    PaymentCreate, PaymentRead, PricingRuleRead,
)
from app.services.auth import require_admin
from app.services.inference_proxy import InferenceProxy
from app.services.billing import (
    ensure_default_billing_plans, generate_monthly_invoices,
    list_client_billing_snapshots, refresh_billing_statuses, serialize_invoice,
)
from app.services.security_monitor import log_security_event, observe_billing_status_metrics
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/admin", tags=["admin-billing"], dependencies=[Depends(require_admin)])
settings = get_settings()


def _serialize_billing_plan_payload(payload: BillingPlanCreate) -> dict:
    plan_data = payload.model_dump()
    allowed_models = plan_data.pop("allowed_models", None)
    plan_data["allowed_models_json"] = json.dumps(allowed_models) if allowed_models is not None else None
    routing_policy = plan_data.pop("routing_policy", None)
    plan_data["routing_policy_json"] = json.dumps(routing_policy) if routing_policy is not None else None
    return plan_data


from app.domains.billing.contracts import BillingRepository
from app.domains.billing.repositories import SqlAlchemyBillingRepository

@router.get("/billing/plans", response_model=list[BillingPlanRead])
async def list_billing_plans(session: AsyncSession = Depends(get_db_session)):
    result = await session.execute(select(BillingPlan).order_by(BillingPlan.created_at.asc()))
    return result.scalars().all()


@router.post("/billing/plans", response_model=BillingPlanRead, status_code=201)
async def create_billing_plan(payload: BillingPlanCreate, session: AsyncSession = Depends(get_db_session)):
    existing = await session.execute(select(BillingPlan).where(BillingPlan.code == payload.code))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="billing plan code already exists")
    plan_data = _serialize_billing_plan_payload(payload)
    plan = BillingPlan(**plan_data)
    session.add(plan)
    await session.commit()
    await session.refresh(plan)
    return plan


@router.patch("/billing/plans/{plan_id}", response_model=BillingPlanRead)
async def patch_billing_plan(
    plan_id: uuid.UUID,
    payload: BillingPlanPatch,
    session: AsyncSession = Depends(get_db_session),
):
    plan = await session.get(BillingPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="billing plan not found")
    patch_data = payload.model_dump(exclude_unset=True)
    if "allowed_models" in patch_data:
        allowed_models = patch_data.pop("allowed_models")
        patch_data["allowed_models_json"] = json.dumps(allowed_models) if allowed_models is not None else None
    if "routing_policy" in patch_data:
        routing_policy = patch_data.pop("routing_policy")
        patch_data["routing_policy_json"] = json.dumps(routing_policy) if routing_policy is not None else None
    for key, value in patch_data.items():
        setattr(plan, key, value)
    plan.updated_at = utc_now()
    await session.commit()
    await session.refresh(plan)
    return plan


@router.get("/billing/pricing-rules", response_model=list[PricingRuleRead])
async def list_pricing_rules(session: AsyncSession = Depends(get_db_session)):
    rows = (await session.execute(select(PricingRule).order_by(PricingRule.created_at.asc()))).scalars().all()
    return [
        PricingRuleRead(
            id=row.id,
            billing_plan_id=row.billing_plan_id,
            currency=row.currency,
            monthly_price=float(row.monthly_price),
            overage_price_per_1k_tokens=float(row.overage_price_per_1k_tokens),
            description=row.description,
            is_active=row.is_active,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row in rows
    ]


@router.patch("/billing/plans/{plan_id}/models", response_model=BillingPlanRead)
async def set_billing_plan_models(
    plan_id: uuid.UUID,
    payload: BillingPlanModelsPatch,
    session: AsyncSession = Depends(get_db_session),
):
    plan = await session.get(BillingPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="billing plan not found")
    plan.allowed_models_json = json.dumps(payload.allowed_models)
    plan.updated_at = utc_now()
    await session.commit()
    await session.refresh(plan)
    return plan


@router.get("/billing/invoices/preview")
async def preview_invoices(
    session: AsyncSession = Depends(get_db_session),
    proxy: InferenceProxy = Depends(get_inference_proxy),
):
    await refresh_billing_statuses(session, suspend_after_days=settings.billing_suspend_after_days)
    await session.commit()
    summary = await get_usage_summary(session, proxy)
    return {
        "generated_at": summary["generated_at"],
        "totals": {
            "clients_total": summary["totals"]["clients_total"],
            "estimated_cost_usd": summary["totals"]["estimated_cost_usd"],
        },
        "clients": [
            {
                "client_id": item["client_id"],
                "name": item["name"],
                "billing_plan_code": item["billing_plan_code"],
                "invoice_preview": item["invoice_preview"],
            }
            for item in summary["clients"]
        ],
    }


@router.get("/billing/clients/{client_id}/invoice/preview")
async def preview_client_invoice(
    client_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    proxy: InferenceProxy = Depends(get_inference_proxy),
):
    await refresh_billing_statuses(session, suspend_after_days=settings.billing_suspend_after_days)
    await session.commit()
    summary = await get_usage_summary(session, proxy)
    client_entry = next((item for item in summary["clients"] if item["client_id"] == str(client_id)), None)
    if client_entry is None:
        raise HTTPException(status_code=404, detail="client not found")
    return {
        "client_id": client_entry["client_id"],
        "name": client_entry["name"],
        "billing_plan_code": client_entry["billing_plan_code"],
        "invoice_preview": client_entry["invoice_preview"],
    }


@router.post("/billing/invoices/generate", status_code=201)
async def generate_invoices(payload: InvoiceGenerateRequest, session: AsyncSession = Depends(get_db_session)):
    if payload.client_id is not None and await session.get(Client, payload.client_id) is None:
        raise HTTPException(status_code=404, detail="client not found")
    result = await generate_monthly_invoices(
        session,
        reference_datetime=utc_now(),
        invoice_day=settings.billing_invoice_day,
        due_in_days=payload.due_in_days,
        suspend_after_days=settings.billing_suspend_after_days,
        payment_method=payload.payment_method,
        payment_instructions=payload.payment_instructions,
        force=True,
        client_id=payload.client_id,
    )
    await session.commit()
    created = result["created"]
    updated = result["updated"]
    invoice_ids = [item.id for item in [*created, *updated]]
    invoices_by_id = {}
    if invoice_ids:
        refreshed = (
            await session.execute(
                select(BillingInvoice)
                .options(selectinload(BillingInvoice.payments))
                .where(BillingInvoice.id.in_(invoice_ids))
            )
        ).scalars().all()
        invoices_by_id = {item.id: item for item in refreshed}
    return {
        "generated_at": result["generated_at"],
        "created": [serialize_invoice(invoices_by_id.get(item.id, item)) for item in created],
        "updated": [serialize_invoice(invoices_by_id.get(item.id, item)) for item in updated],
        "skipped": result["skipped"],
        "reason": result["reason"],
    }


@router.post("/billing/run-cycle")
async def run_billing_cycle(session: AsyncSession = Depends(get_db_session)):
    result = await generate_monthly_invoices(
        session,
        reference_datetime=utc_now(),
        invoice_day=settings.billing_invoice_day,
        due_in_days=settings.billing_due_days,
        suspend_after_days=settings.billing_suspend_after_days,
        payment_method="manual_pix",
        payment_instructions="billing-cycle",
        force=False,
    )
    await session.commit()
    await refresh_billing_statuses(session, suspend_after_days=settings.billing_suspend_after_days)
    await session.commit()
    return {
        "generated_at": result["generated_at"],
        "created_count": len(result["created"]),
        "updated_count": len(result["updated"]),
        "skipped_count": len(result["skipped"]),
        "reason": result["reason"],
    }


@router.get("/billing/invoices")
async def list_invoices(
    session: AsyncSession = Depends(get_db_session),
    full: bool = Query(False, description="Return full summary and payments instead of just a list")
):
    await refresh_billing_statuses(session, suspend_after_days=settings.billing_suspend_after_days)
    await session.commit()
    invoices = (
        await session.execute(
            select(BillingInvoice)
            .options(
                selectinload(BillingInvoice.client),
                selectinload(BillingInvoice.billing_plan),
                selectinload(BillingInvoice.payments),
            )
            .order_by(desc(BillingInvoice.created_at))
            .limit(200)
        )
    ).scalars().all()

    serialized_invoices = [
        {
            **serialize_invoice(invoice),
            "client_name": invoice.client.name if invoice.client else None,
            "client_billing_status": invoice.client.billing_status if invoice.client else None,
            "billing_plan_code": invoice.billing_plan.code if invoice.billing_plan else None,
        }
        for invoice in invoices
    ]

    if not full:
        return serialized_invoices

    payments = (
        await session.execute(
            select(CustomerPayment)
            .order_by(desc(CustomerPayment.created_at))
            .limit(200)
        )
    ).scalars().all()

    return {
        "generated_at": utc_now().isoformat(),
        "summary": {
            "overdue_invoices": sum(1 for invoice in invoices if invoice.status == "overdue"),
            "past_due_clients": len({str(invoice.client_id) for invoice in invoices if invoice.client and invoice.client.billing_status == "past_due"}),
            "suspended_clients": len({str(invoice.client_id) for invoice in invoices if invoice.client and invoice.client.billing_status == "suspended"}),
        },
        "invoices": serialized_invoices,
        "payments": [
            {
                "id": str(payment.id),
                "invoice_id": str(payment.invoice_id),
                "client_id": str(payment.client_id),
                "status": payment.status,
                "amount": float(payment.amount),
                "currency": payment.currency,
                "payment_method": payment.payment_method,
                "payment_reference": payment.payment_reference,
                "note": payment.note,
                "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
                "cancelled_at": payment.cancelled_at.isoformat() if payment.cancelled_at else None,
                "created_at": payment.created_at.isoformat(),
                "updated_at": payment.updated_at.isoformat(),
            }
            for payment in payments
        ],
    }


@router.patch("/billing/invoices/{invoice_id}/mark-overdue")
async def mark_invoice_overdue(
    invoice_id: uuid.UUID,
    simulate_suspension: bool = Query(default=False),
    session: AsyncSession = Depends(get_db_session)
):
    from datetime import timedelta
    invoice = await session.get(BillingInvoice, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="invoice not found")
    if invoice.status == "paid":
        raise HTTPException(status_code=409, detail="paid invoice cannot be marked overdue")
    invoice.status = "overdue"
    if simulate_suspension:
        invoice.due_at = utc_now() - timedelta(days=settings.billing_suspend_after_days + 1)
    invoice.updated_at = utc_now()
    await session.commit()
    await refresh_billing_statuses(session, suspend_after_days=settings.billing_suspend_after_days)
    await session.commit()
    return {"status": "overdue", "invoice_id": str(invoice.id)}


@router.get("/billing/payments", response_model=list[PaymentRead])
async def list_payments(session: AsyncSession = Depends(get_db_session)):
    result = await session.execute(select(CustomerPayment).order_by(desc(CustomerPayment.created_at)).limit(500))
    return result.scalars().all()


@router.post("/billing/payments", response_model=PaymentRead, status_code=201)
async def create_payment(payload: PaymentCreate, session: AsyncSession = Depends(get_db_session)):
    invoice = await session.get(BillingInvoice, payload.invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="invoice not found")
    payment = CustomerPayment(
        invoice_id=payload.invoice_id,
        client_id=invoice.client_id,
        amount=Decimal(str(payload.amount)),
        currency=payload.currency,
        payment_method=payload.payment_method,
        payment_reference=payload.payment_reference,
        note=payload.note,
        status="paid" if payload.paid_at else "pending",
        paid_at=payload.paid_at,
    )
    session.add(payment)
    if payload.paid_at and invoice.status != "paid":
        # If paying full amount or more, mark invoice as paid
        # Simple logic: if any payment is 'paid', we consider it progress.
        # For simplicity, if this payment is marked 'paid', we mark invoice paid.
        invoice.status = "paid"
        invoice.paid_at = payload.paid_at
        if invoice.client:
            invoice.client.billing_status = "active"
    await session.commit()
    await refresh_billing_statuses(session, suspend_after_days=settings.billing_suspend_after_days)
    await session.commit()
    await session.refresh(payment)
    return payment


@router.patch("/billing/payments/{payment_id}/cancel")
async def cancel_payment(payment_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)):
    payment = await session.get(CustomerPayment, payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="payment not found")
    if payment.status == "cancelled":
        raise HTTPException(status_code=409, detail="payment already cancelled")
    payment.status = "cancelled"
    payment.cancelled_at = utc_now()
    payment.updated_at = utc_now()
    await session.commit()
    return {"status": "cancelled", "payment_id": str(payment.id)}


@router.patch("/billing/invoices/{invoice_id}/mark-paid")
async def mark_invoice_paid(
    invoice_id: uuid.UUID,
    payload: InvoiceMarkPaidRequest,
    session: AsyncSession = Depends(get_db_session),
):
    invoice = (
        await session.execute(
            select(BillingInvoice)
            .options(selectinload(BillingInvoice.client), selectinload(BillingInvoice.payments))
            .where(BillingInvoice.id == invoice_id)
        )
    ).scalar_one_or_none()
    if invoice is None:
        raise HTTPException(status_code=404, detail="invoice not found")
    if invoice.status == "cancelled":
        raise HTTPException(status_code=409, detail="cancelled invoice cannot be paid")
    if invoice.status == "paid":
        raise HTTPException(status_code=409, detail="invoice already paid")

    paid_at = payload.paid_at or utc_now()
    invoice.status = "paid"
    invoice.paid_at = paid_at
    invoice.cancelled_at = None
    invoice.updated_at = utc_now()

    payment = next((item for item in invoice.payments if item.status in {"pending", "overdue"}), None)
    if payment is None:
        payment = CustomerPayment(
            invoice_id=invoice.id,
            client_id=invoice.client_id,
            amount=invoice.total_amount,
            currency=invoice.currency,
            payment_method=payload.payment_method,
            status="paid",
        )
        session.add(payment)
    payment.status = "paid"
    payment.amount = Decimal(str(payload.amount_paid)) if payload.amount_paid is not None else invoice.total_amount
    payment.currency = invoice.currency
    payment.payment_method = payload.payment_method
    payment.payment_reference = payload.payment_reference
    payment.note = payload.note
    payment.paid_at = paid_at
    payment.cancelled_at = None
    payment.updated_at = utc_now()

    if invoice.client is not None:
        invoice.client.billing_status = "active"
        invoice.client.updated_at = utc_now()

    await session.commit()
    await refresh_billing_statuses(session, suspend_after_days=settings.billing_suspend_after_days)
    await session.commit()
    await session.refresh(invoice, attribute_names=["payments", "client"])
    return {
        "status": "paid",
        "invoice": {
            **serialize_invoice(invoice),
            "client_name": invoice.client.name if invoice.client else None,
            "client_billing_status": invoice.client.billing_status if invoice.client else None,
        },
    }


@router.patch("/billing/invoices/{invoice_id}/cancel")
async def cancel_invoice(invoice_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)):
    invoice = (
        await session.execute(
            select(BillingInvoice)
            .options(selectinload(BillingInvoice.client), selectinload(BillingInvoice.payments))
            .where(BillingInvoice.id == invoice_id)
        )
    ).scalar_one_or_none()
    if invoice is None:
        raise HTTPException(status_code=404, detail="invoice not found")
    if invoice.status == "paid":
        raise HTTPException(status_code=409, detail="paid invoice cannot be cancelled")
    if invoice.status == "cancelled":
        raise HTTPException(status_code=409, detail="invoice already cancelled")

    invoice.status = "cancelled"
    invoice.cancelled_at = utc_now()
    invoice.updated_at = utc_now()
    for payment in invoice.payments:
        if payment.status != "paid":
            payment.status = "cancelled"
            payment.cancelled_at = utc_now()
            payment.updated_at = utc_now()

    await session.commit()
    await refresh_billing_statuses(session, suspend_after_days=settings.billing_suspend_after_days)
    await session.commit()
    await session.refresh(invoice, attribute_names=["payments", "client"])
    return {
        "status": "cancelled",
        "invoice": {
            **serialize_invoice(invoice),
            "client_name": invoice.client.name if invoice.client else None,
            "client_billing_status": invoice.client.billing_status if invoice.client else None,
        },
    }
