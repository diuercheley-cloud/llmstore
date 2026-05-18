import json
from enum import Enum
from functools import total_ordering

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.security import verify_secret
from app.core.time import utc_now
from app.db.session import get_db_session, get_redis
from app.models.api_key import ApiKey
from app.models.billing_plan import BillingPlan
from app.models.client import Client
from app.services.admin_rbac import (
    RBAC_ADMIN_PERMISSIONS,
    authenticate_admin_request,
    is_rbac_admin_enabled,
    record_admin_audit_event,
    require_permissions,
    resolve_admin_permission_from_request,
)
from app.services.security_monitor import enforce_client_ip_policy, record_invalid_api_key_attempt

bearer_scheme = HTTPBearer(auto_error=False)
admin_key_scheme = APIKeyHeader(name="X-Admin-Token", auto_error=False)


@total_ordering
class AdminRole(Enum):
    READ = "admin_read"
    WRITE = "admin_write"
    SUPER = "super_admin"

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            order = {AdminRole.READ: 1, AdminRole.WRITE: 2, AdminRole.SUPER: 3}
            return order[self] < order[other]
        return NotImplemented

def get_admin_role(token: str) -> AdminRole | None:
    settings = get_settings()
    if not token:
        return None
    
    # Priority 1: Specific RBAC tokens
    if settings.admin_super_token and token == settings.admin_super_token:
        return AdminRole.SUPER
    if settings.admin_write_token and token == settings.admin_write_token:
        return AdminRole.WRITE
    if settings.admin_read_token and token == settings.admin_read_token:
        return AdminRole.READ
    
    # Priority 2: Fallback to old admin token if super token is not defined
    if not settings.admin_super_token and token == settings.admin_token:
        return AdminRole.SUPER
        
    return None

def _write_like_permissions() -> list[str]:
    permissions = []
    for code in RBAC_ADMIN_PERMISSIONS:
        if code == "superadmin:all" or code.endswith(":write") or code.endswith(":delete"):
            permissions.append(code)
    return permissions


def _role_from_permissions(permission_codes: set[str]) -> AdminRole:
    if "superadmin:all" in permission_codes:
        return AdminRole.SUPER
    if any(code.endswith(":write") or code.endswith(":delete") for code in permission_codes):
        return AdminRole.WRITE
    return AdminRole.READ


async def require_admin(
    request: Request,
    x_admin_token: str = Depends(admin_key_scheme),
    session: AsyncSession = Depends(get_db_session),
):
    if not is_rbac_admin_enabled():
        role = get_admin_role(x_admin_token or "")
        if not role or role < AdminRole.SUPER:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid admin token")
        request.state.admin_role_names = [role.value]
        request.state.admin_permission_codes = []
        return {"role": role.value, "legacy": True}

    admin = await authenticate_admin_request(session=session, request=request, token=x_admin_token or "")
    required_permission = resolve_admin_permission_from_request(request)
    if required_permission and not admin.has_permission(required_permission):
        await record_admin_audit_event(
            session,
            event_type="admin.permission.denied",
            status="denied",
            request=request,
            admin=admin,
            metadata={
                "required_permissions": [required_permission],
                "granted_permissions": sorted(admin.permission_codes),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "forbidden", "required_permissions": [required_permission]},
        )
    return admin


def require_admin_permission(permission: str):
    async def permission_checker(
        request: Request,
        x_admin_token: str = Depends(admin_key_scheme),
        session: AsyncSession = Depends(get_db_session),
    ):
        if not is_rbac_admin_enabled():
            await require_admin(request=request, x_admin_token=x_admin_token, session=session)
            return {"role": AdminRole.SUPER.value, "legacy": True}
        return await require_permissions(
            session=session,
            request=request,
            token=x_admin_token or "",
            permissions=[permission],
        )

    return permission_checker


def require_any_admin_permission(permissions: list[str]):
    async def permission_checker(
        request: Request,
        x_admin_token: str = Depends(admin_key_scheme),
        session: AsyncSession = Depends(get_db_session),
    ):
        if not is_rbac_admin_enabled():
            await require_admin(request=request, x_admin_token=x_admin_token, session=session)
            return {"role": AdminRole.SUPER.value, "legacy": True}
        return await require_permissions(
            session=session,
            request=request,
            token=x_admin_token or "",
            permissions=permissions,
        )

    return permission_checker


async def require_superadmin(
    request: Request,
    x_admin_token: str = Depends(admin_key_scheme),
    session: AsyncSession = Depends(get_db_session),
):
    if not is_rbac_admin_enabled():
        await require_admin(request=request, x_admin_token=x_admin_token, session=session)
        return {"role": AdminRole.SUPER.value, "legacy": True}
    return await require_permissions(
        session=session,
        request=request,
        token=x_admin_token or "",
        permissions=["superadmin:all"],
    )

def require_admin_role(required_role: AdminRole):
    async def role_checker(
        request: Request,
        x_admin_token: str = Depends(admin_key_scheme),
        session: AsyncSession = Depends(get_db_session),
    ) -> AdminRole:
        if not is_rbac_admin_enabled():
            role = get_admin_role(x_admin_token or "")
            if not role:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid admin token")
            if role < required_role:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "forbidden",
                        "requiredRole": required_role.value,
                        "currentRole": role.value,
                    },
                )
            return role

        if required_role == AdminRole.SUPER:
            admin = await require_superadmin(request=request, x_admin_token=x_admin_token, session=session)
        elif required_role == AdminRole.WRITE:
            admin = await require_permissions(
                session=session,
                request=request,
                token=x_admin_token or "",
                permissions=_write_like_permissions(),
            )
        else:
            admin = await authenticate_admin_request(session=session, request=request, token=x_admin_token or "")
        return _role_from_permissions(admin.permission_codes)

    return role_checker


async def require_client(
    auth_creds: str = Depends(bearer_scheme),
    request: Request = None,
    session: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> Client:
    if not auth_creds:
        if request is not None:
            await record_invalid_api_key_attempt(
                session,
                redis,
                source_ip=getattr(request.state, "source_ip", "unknown"),
                api_key_prefix=None,
                reason="missing bearer token",
            )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
    
    plaintext = auth_creds.credentials.strip()
    prefix = plaintext[:12]
    result = await session.execute(
        select(ApiKey).where(ApiKey.key_prefix == prefix, ApiKey.is_active == True, ApiKey.revoked_at.is_(None)).order_by(ApiKey.created_at.desc())
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
    
    # Check expiration
    if api_key.expires_at:
        expires_at = api_key.expires_at
        if expires_at.tzinfo is None:
            from datetime import timezone
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        
        if expires_at < utc_now():
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="api key expired")

    # Check allowed IPs for this specific key
    if api_key.allowed_ips_json:
        source_ip = getattr(request.state, "source_ip", "unknown") if request is not None else "unknown"
        try:
            allowed_ips = json.loads(api_key.allowed_ips_json)
            if allowed_ips and source_ip not in allowed_ips:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"IP {source_ip} not allowed for this API key")
        except json.JSONDecodeError:
            pass

    client_result = await session.execute(
        select(Client).options(selectinload(Client.billing_plan).selectinload(BillingPlan.pricing_rules)).where(Client.id == api_key.client_id)
    )
    client = client_result.scalar_one_or_none()
    if request is not None:
        request.state.api_key_prefix = api_key.key_prefix
        request.state.portal_actor_id = str(api_key.id)
        request.state.portal_actor_name = api_key.name
        try:
            request.state.portal_actor_scopes = json.loads(api_key.scopes_json) if api_key.scopes_json else []
        except json.JSONDecodeError:
            request.state.portal_actor_scopes = []
    if client is None or client.is_blocked:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="client blocked or not found")
    if client.billing_status == "suspended":
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={"error": "billing_suspended", "message": "Access suspended due to overdue payment. Please settle your invoices to restore access."}
        )
    await enforce_client_ip_policy(session, client, getattr(request.state, "source_ip", "unknown") if request is not None else "unknown")
    api_key.last_used_at = utc_now()
    await session.commit()
    return client
