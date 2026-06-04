from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable
from uuid import UUID

from app.core.config import get_settings
from app.core.security import generate_api_key, hash_secret, short_prefix, verify_secret
from app.core.time import utc_now
from app.models.admin_rbac import (
    AdminAuditEvent,
    AdminPermission,
    AdminRoleModel,
    AdminRolePermission,
    AdminUser,
    AdminUserRole,
)
from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

RBAC_ADMIN_PERMISSIONS: dict[str, str] = {
    "clients:read": "Read clients and API keys",
    "clients:write": "Create and update clients and API keys",
    "clients:delete": "Delete clients",
    "billing:read": "Read billing and financial data",
    "billing:write": "Manage billing and financial settings",
    "providers:read": "Read provider configuration",
    "providers:write": "Manage provider configuration",
    "models:read": "Read model and routing data",
    "models:write": "Manage model and routing data",
    "rag:read": "Read RAG resources",
    "rag:write": "Manage RAG resources",
    "rag:delete": "Delete RAG resources",
    "tts:read": "Read TTS resources",
    "tts:write": "Manage TTS resources",
    "security:read": "Read security resources",
    "security:write": "Manage security resources",
    "governance:read": "Read governance resources",
    "governance:write": "Manage governance resources",
    "system:read": "Read system resources",
    "system:write": "Manage system resources",
    "superadmin:all": "Full administrative access",
}

RBAC_ADMIN_ROLES: dict[str, dict[str, Any]] = {
    "superadmin": {
        "description": "Full access to all administrative resources",
        "permissions": ["superadmin:all"],
    },
    "admin": {
        "description": "Full operational administrator except superadmin-only actions",
        "permissions": [
            "clients:read", "clients:write", "clients:delete",
            "billing:read", "billing:write",
            "providers:read", "providers:write",
            "models:read", "models:write",
            "rag:read", "rag:write", "rag:delete",
            "tts:read", "tts:write",
            "security:read", "security:write",
            "governance:read", "governance:write",
            "system:read", "system:write",
        ],
    },
    "operator": {
        "description": "Operational access without destructive client or governance privileges",
        "permissions": [
            "clients:read",
            "billing:read",
            "providers:read", "providers:write",
            "models:read", "models:write",
            "rag:read", "rag:write",
            "tts:read", "tts:write",
            "security:read",
            "governance:read",
            "system:read", "system:write",
        ],
    },
    "billing_manager": {
        "description": "Billing and revenue operations access",
        "permissions": ["billing:read", "billing:write", "clients:read", "system:read"],
    },
    "security_auditor": {
        "description": "Read-focused security and governance visibility",
        "permissions": ["security:read", "governance:read", "system:read", "rag:read"],
    },
    "read_only": {
        "description": "Read-only administrative access",
        "permissions": [
            "clients:read", "billing:read", "providers:read", "models:read",
            "rag:read", "tts:read", "security:read", "governance:read", "system:read",
        ],
    },
}

READ_METHODS = {"GET", "HEAD", "OPTIONS"}
DELETE_PERMISSIONS = {"clients", "rag"}


@dataclass
class AuthenticatedAdmin:
    user: AdminUser
    role_names: list[str]
    permission_codes: set[str]
    token_prefix: str

    @property
    def is_superadmin(self) -> bool:
        return "superadmin:all" in self.permission_codes or "superadmin" in self.role_names

    def has_permission(self, permission: str) -> bool:
        return self.is_superadmin or permission in self.permission_codes


def is_rbac_admin_enabled() -> bool:
    return get_settings().rbac_admin_enabled


def generate_admin_token() -> str:
    return generate_api_key(prefix="adm-local")


def _prefixes_for_domain(domain: str) -> tuple[str, ...]:
    mapping = {
        "clients": ("/admin/clients", "/admin/api-keys", "/admin/sales"),
        "billing": ("/admin/billing", "/admin/wallets", "/admin/payments", "/admin/financial"),
        "providers": ("/admin/providers", "/admin/backends", "/admin/hybrid/providers"),
        "models": (
            "/admin/models", "/admin/routing", "/admin/hybrid/routing", "/admin/inference",
            "/admin/commercial-guardrails", "/admin/backends",
        ),
        "rag": ("/admin/rag", "/admin/hybrid/rag"),
        "tts": ("/admin/tts",),
        "security": (
            "/admin/security", "/admin/abuse", "/admin/crypto", "/admin/aiops",
            "/admin/models/integrity", "/admin/inference/proofs",
        ),
        "governance": (
            "/admin/governance", "/admin/compliance", "/admin/workflows", "/admin/operations",
        ),
        "system": (
            "/admin/health", "/admin/cache", "/admin/requests", "/admin/ops",
            "/admin/ops-center", "/admin/tests", "/admin/system",
        ),
    }
    return mapping[domain]


def resolve_admin_permission_from_request(request: Request) -> str | None:
    path = request.url.path
    method = request.method.upper()
    if not path.startswith("/admin"):
        return None
    if path.startswith("/admin/rbac"):
        return None

    domain = "system"
    for candidate in ("clients", "billing", "providers", "models", "rag", "tts", "security", "governance", "system"):
        if any(path.startswith(prefix) for prefix in _prefixes_for_domain(candidate)):
            domain = candidate
            break

    if method in READ_METHODS:
        return f"{domain}:read"
    if method == "DELETE":
        if domain in DELETE_PERMISSIONS:
            return f"{domain}:delete"
        return f"{domain}:write"
    return f"{domain}:write"


async def ensure_admin_rbac_seed(session: AsyncSession) -> None:
    for code, description in RBAC_ADMIN_PERMISSIONS.items():
        existing = await session.execute(select(AdminPermission).where(AdminPermission.code == code))
        permission = existing.scalar_one_or_none()
        if permission is None:
            session.add(AdminPermission(code=code, description=description))
        else:
            permission.description = description
    await session.flush()

    permissions_by_code = await _permissions_by_code(session)
    for role_name, config in RBAC_ADMIN_ROLES.items():
        existing = await session.execute(select(AdminRoleModel).where(AdminRoleModel.name == role_name))
        role = existing.scalar_one_or_none()
        if role is None:
            role = AdminRoleModel(name=role_name, description=config["description"], is_system=True)
            session.add(role)
            await session.flush()
        else:
            role.description = config["description"]
            role.is_system = True

        current = await session.execute(
            select(AdminRolePermission).where(AdminRolePermission.role_id == role.id)
        )
        current_links = {link.permission_id: link for link in current.scalars().all()}
        desired_ids = {permissions_by_code[code].id for code in config["permissions"]}
        for permission_id, link in list(current_links.items()):
            if permission_id not in desired_ids:
                await session.delete(link)
        for permission_id in desired_ids:
            if permission_id not in current_links:
                session.add(AdminRolePermission(role_id=role.id, permission_id=permission_id))
    await session.flush()

    settings = get_settings()
    if settings.admin_token:
        await ensure_bootstrap_admin_user(session, settings.admin_token)


async def ensure_bootstrap_admin_user(session: AsyncSession, legacy_token: str) -> AdminUser:
    role = await _role_by_name(session, "superadmin")
    existing = await session.execute(
        select(AdminUser)
        .options(selectinload(AdminUser.roles))
        .where(AdminUser.username == "legacy-bootstrap-admin")
    )
    user = existing.scalar_one_or_none()
    token_prefix = short_prefix(legacy_token)
    if user is None:
        user = AdminUser(
            username="legacy-bootstrap-admin",
            email=None,
            display_name="Legacy Bootstrap Admin",
            token_prefix=token_prefix,
            token_hash=hash_secret(legacy_token),
            is_active=True,
            is_legacy_bootstrap=True,
        )
        session.add(user)
        await session.flush()
    else:
        user.display_name = "Legacy Bootstrap Admin"
        user.token_prefix = token_prefix
        user.token_hash = hash_secret(legacy_token)
        user.is_active = True
        user.is_legacy_bootstrap = True

    role_exists = await session.execute(
        select(AdminUserRole).where(AdminUserRole.user_id == user.id, AdminUserRole.role_id == role.id)
    )
    if role_exists.scalar_one_or_none() is None:
        session.add(AdminUserRole(user_id=user.id, role_id=role.id))
    await session.flush()
    return user


async def authenticate_admin_token(
    session: AsyncSession,
    token: str,
) -> AuthenticatedAdmin | None:
    if not token:
        return None
    result = await session.execute(
        select(AdminUser)
        .options(
            selectinload(AdminUser.roles)
            .selectinload(AdminUserRole.role)
            .selectinload(AdminRoleModel.permissions)
            .selectinload(AdminRolePermission.permission)
        )
        .where(AdminUser.token_prefix == short_prefix(token), AdminUser.is_active == True)
        .order_by(AdminUser.created_at.desc())
    )
    for user in result.scalars().all():
        if verify_secret(token, user.token_hash):
            permissions = set()
            role_names = []
            for user_role in user.roles:
                role_names.append(user_role.role.name)
                for role_permission in user_role.role.permissions:
                    permissions.add(role_permission.permission.code)
            return AuthenticatedAdmin(
                user=user,
                role_names=sorted(set(role_names)),
                permission_codes=permissions,
                token_prefix=user.token_prefix,
            )
    return None


async def record_admin_audit_event(
    session: AsyncSession,
    *,
    event_type: str,
    status: str,
    request: Request | None = None,
    admin: AuthenticatedAdmin | None = None,
    actor_identifier: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    metadata: dict[str, Any] | list[Any] | None = None,
) -> None:
    source_ip = getattr(request.state, "source_ip", None) if request is not None else None
    event = AdminAuditEvent(
        admin_user_id=admin.user.id if admin is not None else None,
        event_type=event_type,
        status=status,
        request_path=request.url.path if request is not None else None,
        request_method=request.method if request is not None else None,
        source_ip=source_ip,
        user_agent=request.headers.get("user-agent") if request is not None else None,
        target_type=target_type,
        target_id=target_id,
        actor_identifier=actor_identifier or (admin.user.username if admin is not None else None),
        metadata_json=metadata,
    )
    session.add(event)
    await session.commit()


async def authenticate_admin_request(
    *,
    session: AsyncSession,
    request: Request,
    token: str,
    log_success: bool = True,
) -> AuthenticatedAdmin:
    admin = await authenticate_admin_token(session, token)
    if admin is None:
        await record_admin_audit_event(
            session,
            event_type="admin.auth.failed",
            status="denied",
            request=request,
            actor_identifier=short_prefix(token) if token else "missing-token",
            metadata={"reason": "invalid admin token"},
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid admin token")

    admin.user.last_login_at = utc_now()
    await session.commit()
    if log_success and not getattr(request.state, "admin_auth_audit_logged", False):
        await record_admin_audit_event(
            session,
            event_type="admin.auth.success",
            status="success",
            request=request,
            admin=admin,
            metadata={"roles": admin.role_names},
        )
        request.state.admin_auth_audit_logged = True
    request.state.admin_user = admin.user
    request.state.admin_permission_codes = sorted(admin.permission_codes)
    request.state.admin_role_names = admin.role_names
    return admin


async def require_permissions(
    *,
    session: AsyncSession,
    request: Request,
    token: str,
    permissions: Iterable[str],
    require_all: bool = False,
) -> AuthenticatedAdmin:
    admin = await authenticate_admin_request(session=session, request=request, token=token)
    permission_list = list(permissions)
    allowed = all(admin.has_permission(code) for code in permission_list) if require_all else any(
        admin.has_permission(code) for code in permission_list
    )
    if allowed:
        return admin

    from app.core.metrics import record_rbac_denial
    record_rbac_denial(
        client_id=str(getattr(admin, "client_id", admin.user.id)),
        resource=request.url.path,
        action=",".join(permission_list)
    )

    await record_admin_audit_event(
        session,
        event_type="admin.permission.denied",
        status="denied",
        request=request,
        admin=admin,
        metadata={
            "required_permissions": permission_list,
            "granted_permissions": sorted(admin.permission_codes),
        },
    )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"error": "forbidden", "required_permissions": permission_list},
    )


async def assign_roles_to_user(
    session: AsyncSession,
    *,
    user: AdminUser,
    role_ids: list[UUID] | None = None,
    role_names: list[str] | None = None,
) -> None:
    role_ids = role_ids or []
    role_names = role_names or []
    desired_roles = await _load_roles(session, role_ids=role_ids, role_names=role_names)
    current = await session.execute(select(AdminUserRole).where(AdminUserRole.user_id == user.id))
    current_links = current.scalars().all()
    current_ids = {link.role_id for link in current_links}
    desired_ids = {role.id for role in desired_roles}
    for link in current_links:
        if link.role_id not in desired_ids:
            await session.delete(link)
    for role in desired_roles:
        if role.id not in current_ids:
            session.add(AdminUserRole(user_id=user.id, role_id=role.id))
    await session.flush()


async def sync_role_permissions(
    session: AsyncSession,
    *,
    role: AdminRoleModel,
    permission_codes: list[str],
) -> None:
    permissions_by_code = await _permissions_by_code(session)
    missing = [code for code in permission_codes if code not in permissions_by_code]
    if missing:
        raise HTTPException(status_code=400, detail={"error": "unknown_permissions", "codes": missing})

    current = await session.execute(select(AdminRolePermission).where(AdminRolePermission.role_id == role.id))
    current_links = current.scalars().all()
    current_ids = {link.permission_id for link in current_links}
    desired_ids = {permissions_by_code[code].id for code in permission_codes}
    for link in current_links:
        if link.permission_id not in desired_ids:
            await session.delete(link)
    for permission_id in desired_ids:
        if permission_id not in current_ids:
            session.add(AdminRolePermission(role_id=role.id, permission_id=permission_id))
    await session.flush()


async def serialize_admin_user(session: AsyncSession, user: AdminUser) -> dict[str, Any]:
    result = await session.execute(
        select(AdminUser)
        .options(
            selectinload(AdminUser.roles)
            .selectinload(AdminUserRole.role)
            .selectinload(AdminRoleModel.permissions)
            .selectinload(AdminRolePermission.permission)
        )
        .where(AdminUser.id == user.id)
    )
    fresh = result.scalar_one()
    role_ids = [link.role.id for link in fresh.roles]
    role_names = [link.role.name for link in fresh.roles]
    permission_codes = sorted(
        {
            role_permission.permission.code
            for link in fresh.roles
            for role_permission in link.role.permissions
        }
    )
    return {
        "id": fresh.id,
        "username": fresh.username,
        "email": fresh.email,
        "display_name": fresh.display_name,
        "is_active": fresh.is_active,
        "is_legacy_bootstrap": fresh.is_legacy_bootstrap,
        "role_ids": role_ids,
        "role_names": role_names,
        "permission_codes": permission_codes,
        "last_login_at": fresh.last_login_at,
        "created_at": fresh.created_at,
        "updated_at": fresh.updated_at,
    }


async def serialize_role(session: AsyncSession, role: AdminRoleModel) -> dict[str, Any]:
    result = await session.execute(
        select(AdminRoleModel)
        .options(selectinload(AdminRoleModel.permissions).selectinload(AdminRolePermission.permission))
        .where(AdminRoleModel.id == role.id)
    )
    fresh = result.scalar_one()
    return {
        "id": fresh.id,
        "name": fresh.name,
        "description": fresh.description,
        "is_system": fresh.is_system,
        "permission_codes": sorted([link.permission.code for link in fresh.permissions]),
        "created_at": fresh.created_at,
        "updated_at": fresh.updated_at,
    }


async def _permissions_by_code(session: AsyncSession) -> dict[str, AdminPermission]:
    result = await session.execute(select(AdminPermission))
    return {permission.code: permission for permission in result.scalars().all()}


async def _role_by_name(session: AsyncSession, name: str) -> AdminRoleModel:
    result = await session.execute(select(AdminRoleModel).where(AdminRoleModel.name == name))
    role = result.scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=400, detail=f"role not found: {name}")
    return role


async def _load_roles(
    session: AsyncSession,
    *,
    role_ids: list[UUID],
    role_names: list[str],
) -> list[AdminRoleModel]:
    roles: dict[UUID, AdminRoleModel] = {}
    if role_ids:
        result = await session.execute(select(AdminRoleModel).where(AdminRoleModel.id.in_(role_ids)))
        for role in result.scalars().all():
            roles[role.id] = role
        missing = {str(role_id) for role_id in role_ids if role_id not in roles}
        if missing:
            raise HTTPException(status_code=400, detail={"error": "unknown_roles", "ids": sorted(missing)})
    if role_names:
        result = await session.execute(select(AdminRoleModel).where(AdminRoleModel.name.in_(role_names)))
        found_by_name = {role.name: role for role in result.scalars().all()}
        missing = sorted(set(role_names) - set(found_by_name))
        if missing:
            raise HTTPException(status_code=400, detail={"error": "unknown_roles", "names": missing})
        for role in found_by_name.values():
            roles[role.id] = role
    return list(roles.values())
