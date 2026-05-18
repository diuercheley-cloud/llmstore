from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AdminPermissionCreate(BaseModel):
    code: str = Field(min_length=3, max_length=120)
    description: str | None = None


class AdminPermissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class AdminRoleCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = None
    permission_codes: list[str] = Field(default_factory=list)


class AdminRolePatch(BaseModel):
    description: str | None = None
    permission_codes: list[str] | None = None


class AdminRoleRead(BaseModel):
    id: UUID
    name: str
    description: str | None
    is_system: bool
    permission_codes: list[str]
    created_at: datetime
    updated_at: datetime


class AdminUserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=120)
    email: str | None = None
    display_name: str | None = Field(default=None, max_length=255)
    is_active: bool = True
    role_ids: list[UUID] = Field(default_factory=list)
    role_names: list[str] = Field(default_factory=list)
    token: str | None = None


class AdminUserPatch(BaseModel):
    email: str | None = None
    display_name: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None
    role_ids: list[UUID] | None = None
    role_names: list[str] | None = None
    rotate_token: bool = False


class AdminUserRead(BaseModel):
    id: UUID
    username: str
    email: str | None
    display_name: str | None
    is_active: bool
    is_legacy_bootstrap: bool
    role_ids: list[UUID]
    role_names: list[str]
    permission_codes: list[str]
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AdminUserCreateResponse(BaseModel):
    user: AdminUserRead
    admin_token: str


class AdminUserPatchResponse(BaseModel):
    user: AdminUserRead
    admin_token: str | None = None


class AdminUserRoleAssignRequest(BaseModel):
    role_ids: list[UUID] = Field(default_factory=list)
    role_names: list[str] = Field(default_factory=list)
