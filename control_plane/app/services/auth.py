from datetime import datetime

from fastapi import Depends, Header, HTTPException, Request, status
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import verify_secret
from app.core.time import utc_now
from app.db.session import get_db_session, get_redis
from app.models.api_key import ApiKey
from app.models.billing_plan import BillingPlan
from app.models.client import Client
from app.services.security_monitor import enforce_client_ip_policy, record_invalid_api_key_attempt


async def require_admin(x_admin_token: str = Header(default="")) -> None:
    settings = get_settings()
    if x_admin_token != settings.admin_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid admin token")


async def require_client(
    authorization: str = Header(default=""),
    request: Request = None,
    session: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> Client:
    if not authorization.startswith("Bearer "):
        if request is not None:
            await record_invalid_api_key_attempt(
                session,
                redis,
                source_ip=getattr(request.state, "source_ip", "unknown"),
                api_key_prefix=None,
                reason="missing bearer token",
            )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
    plaintext = authorization.removeprefix("Bearer ").strip()
    prefix = plaintext[:12]
    result = await session.execute(
        select(ApiKey).where(ApiKey.key_prefix == prefix, ApiKey.revoked_at.is_(None)).order_by(ApiKey.created_at.desc())
    )
    api_keys = result.scalars().all()
    api_key = next((item for item in api_keys if verify_secret(plaintext, item.key_hash)), None)
    if not api_key:
        await record_invalid_api_key_attempt(
            session,
            redis,
            source_ip=getattr(request.state, "source_ip", "unknown") if request is not None else "unknown",
            api_key_prefix=prefix,
            reason="invalid api key",
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid api key")
    client_result = await session.execute(
        select(Client).options(selectinload(Client.billing_plan).selectinload(BillingPlan.pricing_rules)).where(Client.id == api_key.client_id)
    )
    client = client_result.scalar_one_or_none()
    if client is None or client.is_blocked:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="client blocked or not found")
    if client.billing_status == "suspended":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="client suspended for billing")
    await enforce_client_ip_policy(session, client, getattr(request.state, "source_ip", "unknown") if request is not None else "unknown")
    api_key.last_used_at = utc_now()
    await session.flush()
    return client
