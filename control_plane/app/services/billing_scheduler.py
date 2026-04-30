import asyncio
import logging

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.billing import generate_monthly_invoices, refresh_billing_statuses

logger = logging.getLogger(__name__)


async def run_billing_cycle_once() -> dict:
    settings = get_settings()
    async with SessionLocal() as session:
        result = await generate_monthly_invoices(
            session,
            invoice_day=settings.billing_invoice_day,
            due_in_days=settings.billing_due_days,
            suspend_after_days=settings.billing_suspend_after_days,
            payment_method="manual_pix",
            payment_instructions="billing-cycle",
            force=False,
        )
        refresh_result = await refresh_billing_statuses(
            session,
            suspend_after_days=settings.billing_suspend_after_days,
        )
        await session.commit()
        return {
            "generated_at": result["generated_at"],
            "created_count": len(result["created"]),
            "updated_count": len(result["updated"]),
            "skipped_count": len(result["skipped"]),
            "reason": result["reason"],
            "status_updates": refresh_result,
        }


async def billing_scheduler_loop(stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        try:
            result = await run_billing_cycle_once()
            logger.info("billing cycle executed", extra={"extra_data": result})
        except Exception as exc:
            logger.exception("billing cycle failed", extra={"extra_data": {"error": str(exc)}})
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=3600)
        except asyncio.TimeoutError:
            continue
