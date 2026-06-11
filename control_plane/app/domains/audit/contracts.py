from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from datetime import datetime
from pydantic import BaseModel

class AuditEntryData(BaseModel):
    id: str
    timestamp: datetime
    action: str
    actor: str
    payload: Dict[str, Any]
    tenant_id: str

@runtime_checkable
class AuditRepository(Protocol):
    async def record_event(self, entry: AuditEntryData) -> None: ...
    async def list_events(self, limit: int = 100) -> List[AuditEntryData]: ...
    async def get_event_by_id(self, event_id: str) -> Optional[AuditEntryData]: ...
