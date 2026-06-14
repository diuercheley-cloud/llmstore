# Owner: platform-ops
from app.services.runtime_dependencies import get_db_session
from app.services.payment_topups import process_payment_webhook
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/webhooks/{provider}")
async def payment_webhook(
    provider: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    result = await process_payment_webhook(session, provider=provider, request=request)
    await session.commit()
    return result
