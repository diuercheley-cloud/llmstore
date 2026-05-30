from functools import lru_cache

from fastapi import Depends
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session, get_redis
from app.services.auth import (
    AdminRole,
    admin_key_scheme,
    get_admin_role,
    require_admin_permission,
    require_admin_role,
    require_superadmin,
    require_admin,
    require_client,
)
from app.services.backend_slot_manager import BackendSlotManager
from app.services.circuit_breaker import CircuitBreaker
from app.services.inference_proxy import InferenceProxy
from app.services.queue_manager import QueueManager


@lru_cache
def get_queue_manager() -> QueueManager:
    return QueueManager(get_backend_slot_manager())


@lru_cache
def get_backend_slot_manager() -> BackendSlotManager:
    return BackendSlotManager()


@lru_cache
def get_circuit_breaker() -> CircuitBreaker:
    return CircuitBreaker()


@lru_cache
def get_inference_proxy() -> InferenceProxy:
    return InferenceProxy(get_queue_manager(), get_circuit_breaker())


async def get_db(
    session: AsyncSession = Depends(get_db_session),
) -> AsyncSession:
    return session


async def get_admin_db(
    session: AsyncSession = Depends(get_db_session),
    _role=Depends(require_admin_permission("system:read")),
) -> AsyncSession:
    return session


async def get_super_admin_db(
    session: AsyncSession = Depends(get_db_session),
    _role=Depends(require_superadmin),
) -> AsyncSession:
    return session


async def get_admin_token(x_admin_token: str = Depends(admin_key_scheme)) -> str:
    role = get_admin_role(x_admin_token or "")
    if role is None or role < AdminRole.SUPER:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid admin token")
    return x_admin_token or ""


async def get_admin_user(
    admin=Depends(require_superadmin),
) -> dict[str, str]:
    if isinstance(admin, dict):
        return admin
    return {"role": "superadmin"}


class AdminUserContext:
    def __init__(self, tenant_id: str = "default", email: str = "admin@example.com", role: str = "superadmin"):
        self.tenant_id = tenant_id
        self.email = email
        self.role = role


async def get_current_admin_user(
    admin=Depends(require_superadmin),
) -> AdminUserContext:
    email = "admin@example.com"
    tenant_id = "default"
    if isinstance(admin, dict):
        email = admin.get("email", email)
        tenant_id = admin.get("tenant_id", tenant_id)
    else:
        # AuthenticatedAdmin
        email = getattr(admin.user, "email", email) or email
        # If there's username or username has tenant info
        tenant_id = getattr(admin.user, "tenant_id", "default")
    return AdminUserContext(tenant_id=tenant_id, email=email)


async def get_current_user(
    client=Depends(require_client),
):
    if not hasattr(client, "tenant_id"):
        client.tenant_id = client.name
    return client


