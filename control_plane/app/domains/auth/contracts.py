from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from pydantic import BaseModel

class UserData(BaseModel):
    id: str
    username: str
    email: Optional[str] = None
    display_name: Optional[str] = None
    is_active: bool = True
    token_prefix: Optional[str] = None
    token_hash: Optional[str] = None
    roles: List[str] = []
    permissions: List[str] = []

@runtime_checkable
class AuthRepository(Protocol):
    async def get_user_by_id(self, user_id: str) -> Optional[UserData]: ...
    async def get_user_by_username(self, username: str) -> Optional[UserData]: ...
    async def get_user_by_token_prefix(self, prefix: str) -> List[UserData]: ...
    async def list_users(self) -> List[UserData]: ...
    async def create_user(self, user: UserData, token_hash: str, token_prefix: str) -> UserData: ...
    async def update_last_login(self, user_id: str) -> None: ...
