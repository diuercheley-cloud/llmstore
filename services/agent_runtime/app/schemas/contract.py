import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class AgentRunStartRequest(BaseModel):
    agent_id: uuid.UUID
    tenant_id: str
    input_text: str
    user_id: Optional[str] = None
    correlation_id: Optional[str] = None
    session_id: Optional[uuid.UUID] = None
    is_simulation: bool = False
    idempotency_key: Optional[str] = None

class AgentRunResponse(BaseModel):
    id: uuid.UUID
    agent_id: uuid.UUID
    tenant_id: str
    status: str
    created_at: str

class AgentRunActionResponse(BaseModel):
    id: uuid.UUID
    status: str
    message: str
