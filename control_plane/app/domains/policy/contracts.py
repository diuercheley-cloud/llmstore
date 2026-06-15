from typing import Protocol, runtime_checkable

from pydantic import BaseModel


class PolicyData(BaseModel):
    id: str
    client_id: str
    name: str
    scope: str
    version: str
    dsl: str
    status: str
    hash: str
    immutable_hash: str


@runtime_checkable
class PolicyRepository(Protocol):
    async def get_policy_by_id(self, policy_id: str) -> PolicyData | None: ...
    async def list_policies_by_client(self, client_id: str) -> list[PolicyData]: ...
    async def list_all_policies(self) -> list[PolicyData]: ...
    async def save_policy(self, policy: PolicyData) -> PolicyData: ...
    async def delete_policy(self, policy_id: str) -> None: ...
