from __future__ import annotations

import json
import uuid
from decimal import Decimal

from app.core.time import utc_now
from app.models.ai_wallet import AiWallet, AiWalletTransaction
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class InsufficientBalance(Exception):
    pass


class InvalidTransactionType(Exception):
    pass


class WalletNotFound(Exception):
    pass


class DuplicateIdempotencyKey(Exception):
    pass


async def get_or_create_wallet(session: AsyncSession, client_id: uuid.UUID) -> AiWallet:
    wallet = await session.get(AiWallet, client_id)
    if wallet is not None:
        return wallet
    wallet = (
        await session.execute(
            select(AiWallet).where(AiWallet.client_id == client_id)
        )
    ).scalar_one_or_none()
    if wallet is not None:
        return wallet
    wallet = AiWallet(
        client_id=client_id,
        currency="BRL",
        balance_brl=Decimal("0.0000"),
        reserved_brl=Decimal("0.0000"),
        status="active",
    )
    session.add(wallet)
    await session.flush()
    return wallet


async def _record_transaction(
    session: AsyncSession,
    wallet: AiWallet,
    client_id: uuid.UUID,
    tx_type: str,
    amount_brl: Decimal,
    balance_after_brl: Decimal,
    *,
    reference_type: str | None = None,
    reference_id: str | None = None,
    idempotency_key: str | None = None,
    metadata_json: str | None = None,
    created_by: str = "system",
) -> AiWalletTransaction:
    tx = AiWalletTransaction(
        wallet_id=wallet.id,
        client_id=client_id,
        type=tx_type,
        amount_brl=amount_brl,
        balance_after_brl=balance_after_brl,
        reference_type=reference_type,
        reference_id=reference_id,
        idempotency_key=idempotency_key,
        metadata_json=metadata_json,
        created_by=created_by,
    )
    session.add(tx)
    return tx


async def ensure_idempotency(
    session: AsyncSession, idempotency_key: str
) -> AiWalletTransaction | None:
    if not idempotency_key:
        return None
    tx = (
        await session.execute(
            select(AiWalletTransaction).where(
                AiWalletTransaction.idempotency_key == idempotency_key
            )
        )
    ).scalar_one_or_none()
    return tx


async def credit_manual(
    session: AsyncSession,
    client_id: uuid.UUID,
    amount_brl: Decimal,
    *,
    reason: str | None = None,
    idempotency_key: str | None = None,
    created_by: str = "admin",
) -> AiWalletTransaction:
    if idempotency_key:
        existing = await ensure_idempotency(session, idempotency_key)
        if existing is not None:
            return existing
    wallet = await get_or_create_wallet(session, client_id)
    if amount_brl <= 0:
        raise ValueError("credit amount must be positive")
    new_balance = wallet.balance_brl + amount_brl
    wallet.balance_brl = new_balance
    wallet.updated_at = utc_now()
    meta = {}
    if reason:
        meta["reason"] = reason
    tx = await _record_transaction(
        session, wallet, client_id,
        tx_type="manual_credit",
        amount_brl=amount_brl,
        balance_after_brl=new_balance,
        idempotency_key=idempotency_key,
        metadata_json=json.dumps(meta) if meta else None,
        created_by=created_by,
    )
    return tx


async def credit_wallet_topup(
    session: AsyncSession,
    client_id: uuid.UUID,
    amount_brl: Decimal,
    *,
    provider: str,
    external_id: str | None,
    idempotency_key: str,
) -> AiWalletTransaction:
    existing = await ensure_idempotency(session, idempotency_key)
    if existing is not None:
        return existing
    wallet = await get_or_create_wallet(session, client_id)
    if amount_brl <= 0:
        raise ValueError("topup amount must be positive")
    new_balance = wallet.balance_brl + amount_brl
    wallet.balance_brl = new_balance
    wallet.updated_at = utc_now()
    metadata = {"provider": provider}
    if external_id:
        metadata["external_id"] = external_id
    return await _record_transaction(
        session,
        wallet,
        client_id,
        tx_type="future_pix_credit",
        amount_brl=amount_brl,
        balance_after_brl=new_balance,
        reference_type="wallet_topup",
        reference_id=external_id,
        idempotency_key=idempotency_key,
        metadata_json=json.dumps(metadata),
        created_by="payment_webhook",
    )


async def debit_usage(
    session: AsyncSession,
    client_id: uuid.UUID,
    amount_brl: Decimal,
    *,
    reference_type: str | None = None,
    reference_id: str | None = None,
    metadata_json: str | None = None,
) -> AiWalletTransaction:
    wallet = await get_or_create_wallet(session, client_id)
    if amount_brl <= 0:
        raise ValueError("debit amount must be positive")
    available = wallet.balance_brl - wallet.reserved_brl
    if available < amount_brl:
        raise InsufficientBalance(
            f"insufficient balance: available={available:.4f}, required={amount_brl:.4f}"
        )
    new_balance = wallet.balance_brl - amount_brl
    wallet.balance_brl = new_balance
    wallet.updated_at = utc_now()
    tx = await _record_transaction(
        session, wallet, client_id,
        tx_type="usage_debit",
        amount_brl=-amount_brl,
        balance_after_brl=new_balance,
        reference_type=reference_type,
        reference_id=reference_id,
        metadata_json=metadata_json,
        created_by="system",
    )
    return tx


async def reserve_amount(
    session: AsyncSession,
    client_id: uuid.UUID,
    amount_brl: Decimal,
    *,
    reference_type: str | None = None,
    reference_id: str | None = None,
) -> AiWalletTransaction:
    wallet = await get_or_create_wallet(session, client_id)
    if amount_brl <= 0:
        raise ValueError("reserve amount must be positive")
    available = wallet.balance_brl - wallet.reserved_brl
    if available < amount_brl:
        raise InsufficientBalance(
            f"insufficient balance for reservation: available={available:.4f}, required={amount_brl:.4f}"
        )
    wallet.reserved_brl += amount_brl
    wallet.updated_at = utc_now()
    tx = await _record_transaction(
        session, wallet, client_id,
        tx_type="reservation",
        amount_brl=Decimal("0.0000"),
        balance_after_brl=wallet.balance_brl,
        reference_type=reference_type,
        reference_id=reference_id,
        created_by="system",
    )
    return tx


async def release_reservation(
    session: AsyncSession,
    client_id: uuid.UUID,
    amount_brl: Decimal,
    *,
    reference_type: str | None = None,
    reference_id: str | None = None,
) -> AiWalletTransaction:
    wallet = await get_or_create_wallet(session, client_id)
    if amount_brl <= 0:
        raise ValueError("release amount must be positive")
    new_reserved = max(wallet.reserved_brl - amount_brl, Decimal("0.0000"))
    wallet.reserved_brl = new_reserved
    wallet.updated_at = utc_now()
    tx = await _record_transaction(
        session, wallet, client_id,
        tx_type="release",
        amount_brl=Decimal("0.0000"),
        balance_after_brl=wallet.balance_brl,
        reference_type=reference_type,
        reference_id=reference_id,
        created_by="system",
    )
    return tx


async def refund(
    session: AsyncSession,
    client_id: uuid.UUID,
    amount_brl: Decimal,
    *,
    reason: str | None = None,
    reference_type: str | None = None,
    reference_id: str | None = None,
) -> AiWalletTransaction:
    wallet = await get_or_create_wallet(session, client_id)
    if amount_brl <= 0:
        raise ValueError("refund amount must be positive")
    new_balance = wallet.balance_brl + amount_brl
    wallet.balance_brl = new_balance
    wallet.updated_at = utc_now()
    meta = {}
    if reason:
        meta["reason"] = reason
    tx = await _record_transaction(
        session, wallet, client_id,
        tx_type="refund",
        amount_brl=amount_brl,
        balance_after_brl=new_balance,
        reference_type=reference_type,
        reference_id=reference_id,
        metadata_json=json.dumps(meta) if meta else None,
        created_by="system",
    )
    return tx


async def adjustment(
    session: AsyncSession,
    client_id: uuid.UUID,
    amount_brl: Decimal,
    *,
    reason: str | None = None,
    idempotency_key: str | None = None,
    created_by: str = "admin",
) -> AiWalletTransaction:
    if idempotency_key:
        existing = await ensure_idempotency(session, idempotency_key)
        if existing is not None:
            return existing
    wallet = await get_or_create_wallet(session, client_id)
    new_balance = wallet.balance_brl + amount_brl
    if new_balance < 0:
        raise InsufficientBalance(
            f"adjustment would result in negative balance: current={wallet.balance_brl:.4f}, adjustment={amount_brl:.4f}"
        )
    wallet.balance_brl = new_balance
    wallet.updated_at = utc_now()
    meta = {}
    if reason:
        meta["reason"] = reason
    meta["adjustment_type"] = "credit" if amount_brl > 0 else "debit"
    tx = await _record_transaction(
        session, wallet, client_id,
        tx_type="adjustment",
        amount_brl=amount_brl,
        balance_after_brl=new_balance,
        idempotency_key=idempotency_key,
        metadata_json=json.dumps(meta) if meta else None,
        created_by=created_by,
    )
    return tx


async def get_balance(session: AsyncSession, client_id: uuid.UUID) -> dict:
    wallet = await get_or_create_wallet(session, client_id)
    return {
        "wallet_id": str(wallet.id),
        "client_id": str(wallet.client_id),
        "currency": wallet.currency,
        "balance_brl": float(wallet.balance_brl),
        "reserved_brl": float(wallet.reserved_brl),
        "available_brl": float(wallet.balance_brl - wallet.reserved_brl),
        "status": wallet.status,
    }


async def list_transactions(
    session: AsyncSession,
    client_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
) -> list[AiWalletTransaction]:
    result = await session.execute(
        select(AiWalletTransaction)
        .where(AiWalletTransaction.client_id == client_id)
        .order_by(AiWalletTransaction.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


def serialize_transaction(tx: AiWalletTransaction) -> dict:
    return {
        "id": str(tx.id),
        "wallet_id": str(tx.wallet_id),
        "client_id": str(tx.client_id),
        "type": tx.type,
        "amount_brl": float(tx.amount_brl),
        "balance_after_brl": float(tx.balance_after_brl),
        "reference_type": tx.reference_type,
        "reference_id": tx.reference_id,
        "idempotency_key": tx.idempotency_key,
        "metadata_json": tx.metadata_json,
        "created_by": tx.created_by,
        "created_at": tx.created_at.isoformat() if tx.created_at else None,
    }
