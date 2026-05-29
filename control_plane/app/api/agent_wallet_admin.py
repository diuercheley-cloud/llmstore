# Owner: agent-platform
import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.services.agents.wallets.agent_wallet import AgentWalletService
from app.services.agents.wallets.spend_authorization import SpendAuthorization

router = APIRouter(prefix="/admin/agents", tags=["Agent Wallets"])

@router.post("/{agent_id}/wallet")
async def create_agent_wallet(
    agent_id: uuid.UUID,
    tenant_id: str,
    initial_balance: float = 0.0,
    db: AsyncSession = Depends(get_db)
):
    service = AgentWalletService(db)
    return await service.create_wallet(agent_id, tenant_id, initial_balance)

@router.get("/{agent_id}/wallet")
async def get_agent_wallet(
    agent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    service = AgentWalletService(db)
    wallet = await service.get_wallet(agent_id)
    if not wallet: raise HTTPException(status_code=404, detail="Wallet not found")
    return wallet

@router.post("/{agent_id}/wallet/spend")
async def agent_wallet_spend(
    agent_id: uuid.UUID,
    amount: float,
    purpose: str,
    db: AsyncSession = Depends(get_db)
):
    service = AgentWalletService(db)
    try:
        return await service.spend(agent_id, amount, purpose)
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/wallet/authorizations/{auth_id}/approve")
async def approve_spend_authorization(
    auth_id: uuid.UUID,
    approver_id: str,
    db: AsyncSession = Depends(get_db)
):
    service = SpendAuthorization(db)
    await service.approve(auth_id, approver_id)
    return {"status": "approved"}
