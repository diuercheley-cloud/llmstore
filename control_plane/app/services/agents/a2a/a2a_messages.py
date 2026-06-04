# Owner: agent-platform
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class A2AMessagePayload(BaseModel):
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str
    sender_agent_id: str
    recipient_agent_id: str
    content_type: str = "text/plain"
    payload: Dict[str, Any]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    signature: Optional[str] = None

class A2ADelegationPayload(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    delegator_agent_id: str
    delegatee_agent_id: str
    task_description: str
    input_data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    signature: Optional[str] = None
