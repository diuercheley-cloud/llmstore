from typing import Protocol, runtime_checkable

from pydantic import BaseModel


class UserData(BaseModel):
    id: str
    username: str
    email: str | None = None
    display_name: str | None = None
    is_active: bool = True
    token_prefix: str | None = None
    token_hash: str | None = None
    roles: list[str] = []
    permissions: list[str] = []


@runtime_checkable
class AuthRepository(Protocol):
    async def get_user_by_id(self, user_id: str) -> UserData | None: ...
    async def get_user_by_username(self, username: str) -> UserData | None: ...
    async def get_user_by_token_prefix(self, prefix: str) -> list[UserData]: ...
    async def list_users(self) -> list[UserData]: ...
    async def create_user(self, user: UserData, token_hash: str, token_prefix: str) -> UserData: ...
    async def update_last_login(self, user_id: str) -> None: ...
