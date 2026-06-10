# Owner: agent-platform
import hashlib
import hmac
import json
from typing import Any, Dict

from app.core.config import get_settings
from app.models.agents.agents import AgentA2ARegistration
from fastapi import HTTPException
from fastapi.security import APIKeyHeader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

X_A2A_TOKEN_HEADER = APIKeyHeader(name="X-Agent-A2A-Token", auto_error=False)

class A2ASecurityService:
    @staticmethod
    def verify_signature(payload_dict: Dict[str, Any], secret_key: str, signature: str) -> bool:
        # Ensure we exclude 'signature' key itself from signature verification
        payload_copy = {k: v for k, v in payload_dict.items() if k != "signature"}
        serialized = json.dumps(payload_copy, sort_keys=True)
        expected = hmac.new(secret_key.encode(), serialized.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    @staticmethod
    def generate_signature(payload_dict: Dict[str, Any], secret_key: str) -> str:
        payload_copy = {k: v for k, v in payload_dict.items() if k != "signature"}
        serialized = json.dumps(payload_copy, sort_keys=True)
        return hmac.new(secret_key.encode(), serialized.encode(), hashlib.sha256).hexdigest()

    @staticmethod
    def verify_a2a_enabled_or_raise():
        settings = get_settings()
        if not settings.agent_a2a_enabled:
            raise HTTPException(status_code=403, detail="Agentic A2A Protocol is disabled.")

    @staticmethod
    def verify_external_enabled_or_raise():
        settings = get_settings()
        if not settings.agent_a2a_external_enabled:
            raise HTTPException(status_code=403, detail="External Agentic A2A is disabled.")

    @staticmethod
    async def authenticate_agent(db: AsyncSession, token: str) -> AgentA2ARegistration:
        A2ASecurityService.verify_a2a_enabled_or_raise()
        if not token:
            raise HTTPException(status_code=401, detail="Missing A2A authentication token.")

        stmt = select(AgentA2ARegistration).where(AgentA2ARegistration.auth_token == token)
        res = await db.execute(stmt)
        reg = res.scalar_one_or_none()
        if not reg:
            raise HTTPException(status_code=401, detail="Invalid A2A authentication token.")

        if reg.is_external:
            A2ASecurityService.verify_external_enabled_or_raise()

        return reg
