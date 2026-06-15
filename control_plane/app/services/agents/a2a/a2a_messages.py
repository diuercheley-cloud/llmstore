# Owner: agent-platform
import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class A2AMessagePayload(BaseModel):
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str
    sender_agent_id: str
    recipient_agent_id: str
    content_type: str = "text/plain"
    payload: dict[str, Any]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    signature: str | None = None


class A2ADelegationPayload(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    delegator_agent_id: str
    delegatee_agent_id: str
    task_description: str
    input_data: dict[str, Any]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    signature: str | None = None
