import json
import uuid

from app.core.config import get_settings
from app.core.security import generate_api_key, hash_secret, short_prefix
from app.core.time import utc_now
from app.models.billing.billing_plan import BillingPlan
from app.models.core.api_key import ApiKey
from app.models.core.client import Client
from app.schemas.admin import ApiKeyCreate, ApiKeyCreated, ApiKeyRotateResponse
from app.services.auth import require_admin
from app.services.runtime_dependencies import get_db_session
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin", tags=["admin-api-keys"], dependencies=[Depends(require_admin)])
settings = get_settings()


def _serialize_api_key_created(api_key: ApiKey, plaintext: str) -> ApiKeyCreated:
    return ApiKeyCreated(
        id=api_key.id,
        client_id=api_key.client_id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        api_key=plaintext,
        scopes=json.loads(api_key.scopes_json) if api_key.scopes_json else None,
        expires_at=api_key.expires_at,
        allowed_ips=json.loads(api_key.allowed_ips_json) if api_key.allowed_ips_json else None,
        created_at=api_key.created_at,
    )


@router.post("/api-keys", response_model=ApiKeyCreated, status_code=201)
async def create_api_key(payload: ApiKeyCreate, session: AsyncSession = Depends(get_db_session)):
    client = await session.get(Client, payload.client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")
    plaintext = generate_api_key()
    api_key = ApiKey(
        client_id=payload.client_id,
        name=payload.name,
        key_prefix=short_prefix(plaintext),
        key_hash=hash_secret(plaintext),
        scopes_json=json.dumps(payload.scopes) if payload.scopes else None,
        expires_at=payload.expires_at,
        allowed_ips_json=json.dumps(payload.allowed_ips) if payload.allowed_ips else None,
    )
    session.add(api_key)
    await session.commit()
    await session.refresh(api_key)
    return _serialize_api_key_created(api_key, plaintext)


@router.post("/api-keys/{api_key_id}/rotate", response_model=ApiKeyRotateResponse)
async def rotate_api_key(api_key_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)):
    current_key = await session.get(ApiKey, api_key_id)
    if current_key is None:
        raise HTTPException(status_code=404, detail="api key not found")
    if current_key.revoked_at is not None:
        raise HTTPException(status_code=409, detail="api key already revoked")
    plaintext = generate_api_key()
    rotated_key = ApiKey(
        client_id=current_key.client_id,
        name=f"{current_key.name}-rotated",
        key_prefix=short_prefix(plaintext),
        key_hash=hash_secret(plaintext),
        expires_at=current_key.expires_at,
        allowed_ips_json=current_key.allowed_ips_json,
        scopes_json=current_key.scopes_json,
    )
    current_key.revoked_at = utc_now()
    current_key.is_active = False
    session.add(rotated_key)
    await session.commit()
    await session.refresh(rotated_key)
    return ApiKeyRotateResponse(
        rotated_from_id=current_key.id,
        revoked_at=current_key.revoked_at,
        api_key=_serialize_api_key_created(rotated_key, plaintext),
    )


@router.get("/api-keys")
async def list_api_keys(session: AsyncSession = Depends(get_db_session)):
    result = await session.execute(
        select(
            ApiKey,
            Client.name.label("client_name"),
            Client.created_at.label("client_created_at"),
            BillingPlan.name.label("plan_name"),
        )
        .join(Client, Client.id == ApiKey.client_id)
        .outerjoin(BillingPlan, BillingPlan.id == Client.billing_plan_id)
        .order_by(desc(ApiKey.created_at))
        .limit(200)
    )
    rows = result.all()
    return [
        {
            "id": str(api_key.id),
            "client_id": str(api_key.client_id),
            "client_name": client_name,
            "client_created_at": client_created_at.isoformat(),
            "plan_name": plan_name or "N/A",
            "name": api_key.name,
            "key_prefix": api_key.key_prefix,
            "is_active": api_key.is_active,
            "created_at": api_key.created_at.isoformat(),
            "last_used_at": api_key.last_used_at.isoformat() if api_key.last_used_at else None,
            "revoked_at": api_key.revoked_at.isoformat() if api_key.revoked_at else None,
            "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
            "allowed_ips": json.loads(api_key.allowed_ips_json)
            if api_key.allowed_ips_json
            else None,
            "scopes": json.loads(api_key.scopes_json) if api_key.scopes_json else None,
        }
        for api_key, client_name, client_created_at, plan_name in rows
    ]


@router.delete("/api-keys/{api_key_id}", status_code=204)
async def revoke_api_key(api_key_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)):
    api_key = await session.get(ApiKey, api_key_id)
    if api_key is None:
        raise HTTPException(status_code=404, detail="api key not found")
    if not api_key.is_active or api_key.revoked_at is not None:
        await session.delete(api_key)
    else:
        api_key.revoked_at = utc_now()
        api_key.is_active = False
    await session.commit()
