import uuid

from pydantic import BaseModel


class AgentRunStartRequest(BaseModel):
    agent_id: uuid.UUID
    tenant_id: str
    input_text: str
    user_id: str | None = None
    correlation_id: str | None = None
    session_id: uuid.UUID | None = None
    is_simulation: bool = False
    idempotency_key: str | None = None


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
