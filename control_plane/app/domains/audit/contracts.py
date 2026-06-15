from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel


class AuditEntryData(BaseModel):
    id: str
    timestamp: datetime
    action: str
    actor: str
    payload: dict[str, Any]
    tenant_id: str


@runtime_checkable
class AuditRepository(Protocol):
    async def record_event(self, entry: AuditEntryData) -> None: ...
    async def list_events(self, limit: int = 100) -> list[AuditEntryData]: ...
    async def get_event_by_id(self, event_id: str) -> AuditEntryData | None: ...
