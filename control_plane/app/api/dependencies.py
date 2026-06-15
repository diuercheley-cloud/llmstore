from typing import Any

from app.services.auth import require_admin, require_admin_role, require_client
from app.services.runtime_dependencies import get_db_session as get_db_session_dependency
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession


async def get_db() -> AsyncSession:
    async for session in get_db_session_dependency():
        yield session


async def get_current_admin(admin: Any = Depends(require_admin)) -> Any:
    return admin


async def get_admin_user(admin: Any = Depends(require_admin)) -> Any:
    return admin


async def require_admin_user(admin: Any = Depends(require_admin)) -> Any:
    return admin


async def get_current_client(client: Any = Depends(require_client)) -> Any:
    return client


__all__ = [
    "require_admin",
    "require_admin_role",
    "get_db",
    "get_current_admin",
    "get_admin_user",
    "get_current_client",
    "require_admin_user",
]
