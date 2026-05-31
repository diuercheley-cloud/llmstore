import hmac
import hashlib
import json
import logging
import uuid
import httpx
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.agent_deployments import AgentApiDeployment, AgentApiUsageEvent
from app.models.agents import AgentRun
from app.core.time import utc_now

logger = logging.getLogger(__name__)

class DeploymentCallbackService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def trigger_callback(self, run_id: uuid.UUID):
        """Trigger webhook callback for a completed run."""
        # Find usage event to get deployment
        stmt = select(AgentApiUsageEvent).where(AgentApiUsageEvent.run_id == run_id)
        res = await self.db.execute(stmt)
        usage_event = res.scalar_one_or_none()
        if not usage_event:
            return

        deployment = await self.db.get(AgentApiDeployment, usage_event.deployment_id)
        if not deployment or not deployment.callback_url:
            return

        run = await self.db.get(AgentRun, run_id)
        if not run:
            return

        # Prepare payload
        payload = {
            "run_id": str(run.id),
            "deployment_slug": deployment.slug,
            "status": run.status,
            "input": run.input_text,
            "output": None, # In a real system, we'd extract the final answer
            "total_tokens": run.total_tokens,
            "estimated_cost_brl": run.estimated_cost_brl,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        }
        
        # Extract output from steps if completed
        if run.status == "completed":
            from app.services.agents import agent_state
            steps = await agent_state.get_run_steps(self.db, run.id)
            for s in reversed(steps):
                if s.step_type == "final":
                    payload["output"] = s.step_metadata.get("answer") if s.step_metadata else None
                    break

        body = json.dumps(payload)
        headers = {"Content-Type": "application/json"}

        # Sign payload if secret exists
        if deployment.callback_secret:
            signature = hmac.new(
                deployment.callback_secret.encode(),
                body.encode(),
                hashlib.sha256
            ).hexdigest()
            headers["X-Agent-Signature"] = signature

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    deployment.callback_url,
                    content=body,
                    headers=headers
                )
                logger.info(f"Callback sent to {deployment.callback_url} for run {run_id}. Status: {resp.status_code}")
        except Exception as e:
            logger.error(f"Failed to send callback for run {run_id}: {e}")
