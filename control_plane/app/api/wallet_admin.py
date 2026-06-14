# Owner: platform-ops
from decimal import Decimal
from uuid import UUID

from app.services.runtime_dependencies import get_db_session
from app.services.auth import require_admin
from app.services.billing.wallet_service import (
    adjustment,
    credit_manual,
    get_balance,
    list_transactions,
    serialize_transaction,
)
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(
    prefix="/admin/billing/wallets",
    tags=["admin", "billing", "wallets"],
    dependencies=[Depends(require_admin)],
)


class ManualCreditRequest(BaseModel):
    amount_brl: float = Field(..., gt=0, description="Positive credit amount in BRL")
    reason: str | None = None
    idempotency_key: str | None = None


class AdjustmentRequest(BaseModel):
    amount_brl: float = Field(..., description="Can be positive (credit) or negative (debit)")
    reason: str | None = None
    idempotency_key: str | None = None


class WalletBalanceRead(BaseModel):
    wallet_id: str
    client_id: str
    currency: str
    balance_brl: float
    reserved_brl: float
    available_brl: float
    status: str


class WalletTransactionRead(BaseModel):
    id: str
    wallet_id: str
    client_id: str
    type: str
    amount_brl: float
    balance_after_brl: float
    reference_type: str | None = None
    reference_id: str | None = None
    idempotency_key: str | None = None
    metadata_json: str | None = None
    created_by: str
    created_at: str | None = None


@router.get("", response_model=list[WalletBalanceRead])
async def admin_list_wallets(
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    from app.models.billing.ai_wallet import AiWallet
    from sqlalchemy import select
    result = await session.execute(
        select(AiWallet).order_by(AiWallet.created_at.desc()).offset(offset).limit(limit)
    )
    wallets = result.scalars().all()
    return [
        WalletBalanceRead(
            wallet_id=str(w.id),
            client_id=str(w.client_id),
            currency=w.currency,
            balance_brl=float(w.balance_brl),
            reserved_brl=float(w.reserved_brl),
            available_brl=float(w.balance_brl - w.reserved_brl),
            status=w.status,
        )
        for w in wallets
    ]


@router.get("/{client_id}", response_model=WalletBalanceRead)
async def admin_get_wallet(
    client_id: UUID,
    session: AsyncSession = Depends(get_db_session),
):
    balance = await get_balance(session, client_id)
    return WalletBalanceRead(**balance)


@router.post("/{client_id}/manual-credit", response_model=WalletTransactionRead)
async def admin_manual_credit(
    client_id: UUID,
    payload: ManualCreditRequest,
    session: AsyncSession = Depends(get_db_session),
):
    from app.models.core.client import Client
    client = await session.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")
    tx = await credit_manual(
        session,
        client_id,
        Decimal(str(payload.amount_brl)),
        reason=payload.reason,
        idempotency_key=payload.idempotency_key,
        created_by="admin",
    )
    await session.commit()
    return WalletTransactionRead(**serialize_transaction(tx))


@router.post("/{client_id}/adjustment", response_model=WalletTransactionRead)
async def admin_adjustment(
    client_id: UUID,
    payload: AdjustmentRequest,
    session: AsyncSession = Depends(get_db_session),
):
    from app.models.core.client import Client
    from app.services.billing.wallet_service import InsufficientBalance
    client = await session.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")
    try:
        tx = await adjustment(
            session,
            client_id,
            Decimal(str(payload.amount_brl)),
            reason=payload.reason,
            idempotency_key=payload.idempotency_key,
            created_by="admin",
        )
    except InsufficientBalance as e:
        raise HTTPException(status_code=422, detail=str(e))
    await session.commit()
    return WalletTransactionRead(**serialize_transaction(tx))


@router.get("/{client_id}/transactions", response_model=list[WalletTransactionRead])
async def admin_list_transactions(
    client_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    txs = await list_transactions(session, client_id, limit=limit, offset=offset)
    return [WalletTransactionRead(**serialize_transaction(tx)) for tx in txs]
