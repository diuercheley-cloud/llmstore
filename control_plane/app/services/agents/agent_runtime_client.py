import logging
import uuid
from typing import Any

import httpx
from app.core.config import get_settings
from app.services.agents import agent_runtime as internal_runtime
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
settings = get_settings()


class AgentRuntimeClient:
    """
    Client for Agent Runtime.
    Abstraction layer that switches between in-process (legacy) and remote microservice.
    """

    def __init__(self):
        self.is_remote = settings.agent_runtime_service_remote
        self.base_url = settings.agent_runtime_service_url.rstrip("/")
        self.token = settings.agent_runtime_service_token

    async def start_run(
        self,
        db: AsyncSession,
        agent_id: uuid.UUID,
        tenant_id: str,
        input_text: str,
        user_id: str | None = None,
        correlation_id: str | None = None,
        session_id: uuid.UUID | None = None,
        is_simulation: bool = False,
        **kwargs,
    ) -> Any:
        if not self.is_remote:
            return await internal_runtime.start_run(
                db=db,
                agent_id=agent_id,
                tenant_id=tenant_id,
                input_text=input_text,
                user_id=user_id,
                correlation_id=correlation_id,
                session_id=session_id,
                is_simulation=is_simulation,
                **kwargs,
            )

        # Remote mode
        payload = {
            "agent_id": str(agent_id),
            "tenant_id": tenant_id,
            "input_text": input_text,
            "user_id": user_id,
            "correlation_id": correlation_id,
            "session_id": str(session_id) if session_id else None,
            "is_simulation": is_simulation,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/runs", json=payload, headers={"X-Internal-Token": self.token}
                )
                response.raise_for_status()
                # Note: In remote mode, we return a dictionary/schema instead of a DB model
                # The Control Plane API will need to handle both or we need to wrap the response.
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Failed to start remote agent run: {e}")
                raise RuntimeError(f"Agent Runtime Service error: {e}")

    async def pause_run(self, db: AsyncSession, run_id: uuid.UUID) -> Any:
        if not self.is_remote:
            return await internal_runtime.pause_run(db, run_id)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/runs/{run_id}/pause", headers={"X-Internal-Token": self.token}
            )
            response.raise_for_status()
            return response.json()

    async def resume_run(self, db: AsyncSession, run_id: uuid.UUID) -> Any:
        if not self.is_remote:
            return await internal_runtime.resume_run(db, run_id)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/runs/{run_id}/resume", headers={"X-Internal-Token": self.token}
            )
            response.raise_for_status()
            return response.json()

    async def cancel_run(self, db: AsyncSession, run_id: uuid.UUID) -> Any:
        if not self.is_remote:
            return await internal_runtime.cancel_run(db, run_id)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/runs/{run_id}/cancel", headers={"X-Internal-Token": self.token}
            )
            response.raise_for_status()
            return response.json()


_client = None


def get_agent_runtime_client() -> AgentRuntimeClient:
    global _client
    if _client is None:
        _client = AgentRuntimeClient()
    return _client
