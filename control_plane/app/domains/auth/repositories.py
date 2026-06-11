from typing import List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.core.admin_rbac import AdminUser, AdminUserRole, AdminRoleModel, AdminRolePermission, AdminPermission
from .contracts import AuthRepository, UserData
from app.core.time import utc_now

class SqlAlchemyAuthRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _map_user(self, user: AdminUser) -> UserData:
        roles = []
        permissions = set()
        
        if hasattr(user, 'roles'):
            for ur in user.roles:
                roles.append(ur.role.name)
                for rp in ur.role.permissions:
                    permissions.add(rp.permission.code)
                    
        return UserData(
            id=str(user.id),
            username=user.username,
            email=user.email,
            display_name=user.display_name,
            is_active=user.is_active,
            token_prefix=user.token_prefix,
            token_hash=user.token_hash,
            roles=roles,
            permissions=list(permissions)
        )

    async def get_user_by_id(self, user_id: str) -> Optional[UserData]:
        from uuid import UUID
        try:
            user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
        except ValueError:
            return None
            
        stmt = (
            select(AdminUser)
            .where(AdminUser.id == user_uuid)
            .options(
                selectinload(AdminUser.roles)
                .selectinload(AdminUserRole.role)
                .selectinload(AdminRoleModel.permissions)
                .selectinload(AdminRolePermission.permission)
            )
        )
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            return None
        return await self._map_user(user)

    async def get_user_by_username(self, username: str) -> Optional[UserData]:
        stmt = (
            select(AdminUser)
            .where(AdminUser.username == username)
            .options(
                selectinload(AdminUser.roles)
                .selectinload(AdminUserRole.role)
                .selectinload(AdminRoleModel.permissions)
                .selectinload(AdminRolePermission.permission)
            )
        )
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            return None
        return await self._map_user(user)

    async def get_user_by_token_prefix(self, prefix: str) -> List[UserData]:
        stmt = (
            select(AdminUser)
            .where(AdminUser.token_prefix == prefix, AdminUser.is_active == True)
            .order_by(AdminUser.created_at.desc())
            .options(
                selectinload(AdminUser.roles)
                .selectinload(AdminUserRole.role)
                .selectinload(AdminRoleModel.permissions)
                .selectinload(AdminRolePermission.permission)
            )
        )
        result = await self.db.execute(stmt)
        users = result.scalars().all()
        return [await self._map_user(u) for u in users]

    async def list_users(self) -> List[UserData]:
        stmt = (
            select(AdminUser)
            .options(
                selectinload(AdminUser.roles)
                .selectinload(AdminUserRole.role)
                .selectinload(AdminRoleModel.permissions)
                .selectinload(AdminRolePermission.permission)
            )
        )
        result = await self.db.execute(stmt)
        users = result.scalars().all()
        return [await self._map_user(u) for u in users]

    async def create_user(self, user: UserData, token_hash: str, token_prefix: str) -> UserData:
        new_user = AdminUser(
            username=user.username,
            email=user.email,
            display_name=user.display_name,
            token_prefix=token_prefix,
            token_hash=token_hash,
            is_active=user.is_active
        )
        self.db.add(new_user)
        await self.db.flush()
        user.id = str(new_user.id)
        return user

    async def update_last_login(self, user_id: str) -> None:
        from uuid import UUID
        user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
        await self.db.execute(
            update(AdminUser).where(AdminUser.id == user_uuid).values(last_login_at=utc_now())
        )
        await self.db.flush()
