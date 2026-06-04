# Owner: platform-ops
from __future__ import annotations

import uuid

from app.core.security import hash_secret, short_prefix
from app.db.session import get_db_session
from app.models.admin_rbac import (
    AdminAuditEvent,
    AdminPermission,
    AdminRoleModel,
    AdminUser,
    AdminUserRole,
)
from app.schemas.admin_rbac import (
    AdminPermissionCreate,
    AdminPermissionRead,
    AdminRoleCreate,
    AdminRolePatch,
    AdminRoleRead,
    AdminUserCreate,
    AdminUserCreateResponse,
    AdminUserPatch,
    AdminUserPatchResponse,
    AdminUserRead,
    AdminUserRoleAssignRequest,
)
from app.services.admin_rbac import (
    assign_roles_to_user,
    generate_admin_token,
    record_admin_audit_event,
    serialize_admin_user,
    serialize_role,
    sync_role_permissions,
)
from app.services.auth import require_superadmin
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/admin/rbac", tags=["admin_rbac"], dependencies=[Depends(require_superadmin)])


@router.get("/users", response_model=list[AdminUserRead])
async def list_admin_users(
    session: AsyncSession = Depends(get_db_session),
    admin=Depends(require_superadmin),
):
    result = await session.execute(
        select(AdminUser)
        .options(selectinload(AdminUser.roles))
        .order_by(AdminUser.created_at.asc())
    )
    users = result.scalars().all()
    return [AdminUserRead(**await serialize_admin_user(session, user)) for user in users]


@router.post("/users", response_model=AdminUserCreateResponse, status_code=201)
async def create_admin_user(
    payload: AdminUserCreate,
    session: AsyncSession = Depends(get_db_session),
    admin=Depends(require_superadmin),
):
    existing = await session.execute(select(AdminUser).where(AdminUser.username == payload.username))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="admin user already exists")

    token = payload.token or generate_admin_token()
    user = AdminUser(
        username=payload.username,
        email=str(payload.email) if payload.email is not None else None,
        display_name=payload.display_name,
        token_prefix=short_prefix(token),
        token_hash=hash_secret(token),
        is_active=payload.is_active,
    )
    session.add(user)
    await session.flush()
    await assign_roles_to_user(session, user=user, role_ids=payload.role_ids, role_names=payload.role_names)
    await session.commit()
    await record_admin_audit_event(
        session,
        event_type="admin.user.created",
        status="success",
        admin=admin,
        target_type="admin_user",
        target_id=str(user.id),
        metadata={"username": user.username},
    )
    return AdminUserCreateResponse(
        user=AdminUserRead(**await serialize_admin_user(session, user)),
        admin_token=token,
    )


@router.patch("/users/{user_id}", response_model=AdminUserPatchResponse)
async def update_admin_user(
    user_id: uuid.UUID,
    payload: AdminUserPatch,
    session: AsyncSession = Depends(get_db_session),
    admin=Depends(require_superadmin),
):
    user = await session.get(AdminUser, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="admin user not found")

    if payload.email is not None:
        user.email = str(payload.email)
    if payload.display_name is not None:
        user.display_name = payload.display_name
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.role_ids is not None or payload.role_names is not None:
        await assign_roles_to_user(
            session,
            user=user,
            role_ids=payload.role_ids or [],
            role_names=payload.role_names or [],
        )

    issued_token = None
    if payload.rotate_token:
        issued_token = generate_admin_token()
        user.token_prefix = short_prefix(issued_token)
        user.token_hash = hash_secret(issued_token)

    await session.commit()
    await record_admin_audit_event(
        session,
        event_type="admin.user.updated",
        status="success",
        admin=admin,
        target_type="admin_user",
        target_id=str(user.id),
        metadata={"rotate_token": payload.rotate_token},
    )
    return AdminUserPatchResponse(
        user=AdminUserRead(**await serialize_admin_user(session, user)),
        admin_token=issued_token,
    )


@router.delete("/users/{user_id}", status_code=204)
async def delete_admin_user(
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    admin=Depends(require_superadmin),
):
    user = await session.get(AdminUser, user_id)
    if user is None:
        return Response(status_code=204)
    if user.is_legacy_bootstrap:
        raise HTTPException(status_code=400, detail="legacy bootstrap admin cannot be deleted")
    username = user.username
    await session.delete(user)
    await session.commit()
    await record_admin_audit_event(
        session,
        event_type="admin.user.deleted",
        status="success",
        admin=admin,
        target_type="admin_user",
        target_id=str(user_id),
        metadata={"username": username},
    )
    return Response(status_code=204)


@router.get("/roles", response_model=list[AdminRoleRead])
async def list_admin_roles(
    session: AsyncSession = Depends(get_db_session),
    admin=Depends(require_superadmin),
):
    result = await session.execute(
        select(AdminRoleModel)
        .options(selectinload(AdminRoleModel.permissions))
        .order_by(AdminRoleModel.name.asc())
    )
    roles = result.scalars().all()
    return [AdminRoleRead(**await serialize_role(session, role)) for role in roles]


@router.post("/roles", response_model=AdminRoleRead, status_code=201)
async def create_admin_role(
    payload: AdminRoleCreate,
    session: AsyncSession = Depends(get_db_session),
    admin=Depends(require_superadmin),
):
    existing = await session.execute(select(AdminRoleModel).where(AdminRoleModel.name == payload.name))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="admin role already exists")
    role = AdminRoleModel(name=payload.name, description=payload.description, is_system=False)
    session.add(role)
    await session.flush()
    await sync_role_permissions(session, role=role, permission_codes=payload.permission_codes)
    await session.commit()
    await record_admin_audit_event(
        session,
        event_type="admin.role.created",
        status="success",
        admin=admin,
        target_type="admin_role",
        target_id=str(role.id),
        metadata={"name": role.name, "permission_codes": payload.permission_codes},
    )
    return AdminRoleRead(**await serialize_role(session, role))


@router.patch("/roles/{role_id}", response_model=AdminRoleRead)
async def update_admin_role(
    role_id: uuid.UUID,
    payload: AdminRolePatch,
    session: AsyncSession = Depends(get_db_session),
    admin=Depends(require_superadmin),
):
    role = await session.get(AdminRoleModel, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="admin role not found")
    if payload.description is not None:
        role.description = payload.description
    if payload.permission_codes is not None:
        await sync_role_permissions(session, role=role, permission_codes=payload.permission_codes)
    await session.commit()
    await record_admin_audit_event(
        session,
        event_type="admin.role.updated",
        status="success",
        admin=admin,
        target_type="admin_role",
        target_id=str(role.id),
        metadata={"permission_codes": payload.permission_codes},
    )
    return AdminRoleRead(**await serialize_role(session, role))


@router.get("/permissions", response_model=list[AdminPermissionRead])
async def list_admin_permissions(
    session: AsyncSession = Depends(get_db_session),
    admin=Depends(require_superadmin),
):
    result = await session.execute(select(AdminPermission).order_by(AdminPermission.code.asc()))
    return [AdminPermissionRead.model_validate(permission) for permission in result.scalars().all()]


@router.post("/permissions", response_model=AdminPermissionRead, status_code=201)
async def create_admin_permission(
    payload: AdminPermissionCreate,
    session: AsyncSession = Depends(get_db_session),
    admin=Depends(require_superadmin),
):
    existing = await session.execute(select(AdminPermission).where(AdminPermission.code == payload.code))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="admin permission already exists")
    permission = AdminPermission(code=payload.code, description=payload.description)
    session.add(permission)
    await session.commit()
    await record_admin_audit_event(
        session,
        event_type="admin.permission.created",
        status="success",
        admin=admin,
        target_type="admin_permission",
        target_id=str(permission.id),
        metadata={"code": permission.code},
    )
    return AdminPermissionRead.model_validate(permission)


@router.get("/audit")
async def list_admin_audit_events(
    session: AsyncSession = Depends(get_db_session),
    admin=Depends(require_superadmin),
    limit: int = Query(default=100, ge=1, le=1000),
):
    result = await session.execute(
        select(AdminAuditEvent)
        .order_by(AdminAuditEvent.created_at.desc())
        .limit(limit)
    )
    events = result.scalars().all()
    return [
        {
            "id": str(e.id),
            "event_type": e.event_type,
            "status": e.status,
            "actor_identifier": e.actor_identifier,
            "request_path": e.request_path,
            "request_method": e.request_method,
            "status_code": e.metadata_json.get("status_code") if e.metadata_json else None,
            "created_at": e.created_at.isoformat(),
        }
        for e in events
    ]


@router.post("/users/{user_id}/roles", response_model=AdminUserRead)
async def assign_admin_user_roles(
    user_id: uuid.UUID,
    payload: AdminUserRoleAssignRequest,
    session: AsyncSession = Depends(get_db_session),
    admin=Depends(require_superadmin),
):
    user = await session.get(AdminUser, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="admin user not found")
    await assign_roles_to_user(session, user=user, role_ids=payload.role_ids, role_names=payload.role_names)
    await session.commit()
    await record_admin_audit_event(
        session,
        event_type="admin.user.roles_updated",
        status="success",
        admin=admin,
        target_type="admin_user",
        target_id=str(user_id),
        metadata={"role_ids": [str(role_id) for role_id in payload.role_ids], "role_names": payload.role_names},
    )
    return AdminUserRead(**await serialize_admin_user(session, user))


@router.delete("/users/{user_id}/roles/{role_id}", response_model=AdminUserRead)
async def remove_admin_user_role(
    user_id: uuid.UUID,
    role_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    admin=Depends(require_superadmin),
):
    user = await session.get(AdminUser, user_id)
    role = await session.get(AdminRoleModel, role_id)
    if user is None or role is None:
        raise HTTPException(status_code=404, detail="admin user or role not found")
    existing_links = await session.execute(select(AdminUserRole).where(AdminUserRole.user_id == user.id))
    await assign_roles_to_user(
        session,
        user=user,
        role_ids=[link.role_id for link in existing_links.scalars().all() if link.role_id != role_id],
        role_names=[],
    )
    await session.commit()
    await record_admin_audit_event(
        session,
        event_type="admin.user.role_removed",
        status="success",
        admin=admin,
        target_type="admin_user",
        target_id=str(user_id),
        metadata={"role_id": str(role_id)},
    )
    return AdminUserRead(**await serialize_admin_user(session, user))
