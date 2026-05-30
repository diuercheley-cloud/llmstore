# Owner: agent-platform
import uuid
import logging
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_deployments import AgentApiDeployment
from app.services.agent_deployments.agent_api_deployment import (
    AgentApiDeploymentService,
    DeploymentNotFoundError,
)
from app.services.agent_deployments.deployment_router import deployment_router
from app.services.agents import agent_runtime

logger = logging.getLogger(__name__)


class AgentEndpointRegistry:
    """
    Central registry that resolves deployment slugs to agent execution.
    Handles the full invoke pipeline: validation -> rate limit -> concurrency -> execution.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.deployment_svc = AgentApiDeploymentService(db)

    async def resolve_deployment(
        self, slug: str, tenant_id: Optional[str] = None
    ) -> Optional[AgentApiDeployment]:
        """Resolve a slug to an active deployment."""
        if tenant_id:
            return await self.deployment_svc.get_deployment_by_slug(slug, tenant_id)
        # Public resolution (by slug only, for endpoint-key auth)
        return await self.deployment_svc._get_deployment_by_slug(slug)

    async def invoke_async(
        self,
        deployment: AgentApiDeployment,
        input_text: str,
        tenant_id: str,
        client_ip: Optional[str] = None,
        endpoint_key_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """Invoke agent asynchronously via deployment."""
        # Rate limit check
        if not deployment_router.check_rate_limit(deployment):
            await self._log_sla_event(deployment, "rate_limit_exceeded", "warning", {
                "rate_limit_per_minute": deployment.rate_limit_per_minute,
            })
            return {"error": "Rate limit exceeded", "retry_after_seconds": 60}

        # Concurrency check
        if not deployment_router.acquire_concurrency(deployment):
            await self._log_sla_event(deployment, "concurrency_exceeded", "warning", {
                "max_concurrency": deployment.max_concurrency,
                "current": deployment_router.get_concurrent_count(str(deployment.id)),
            })
            return {"error": "Max concurrency exceeded", "retry_after_seconds": 5}

        try:
            run = await agent_runtime.start_run(
                self.db, deployment.agent_id, tenant_id, input_text
            )
            return {"run_id": str(run.id), "status": run.status, "deployment_slug": deployment.slug}
        except Exception as e:
            logger.exception(f"Deployment invoke failed: {deployment.slug}")
            return {"error": str(e)}
        finally:
            deployment_router.release_concurrency(str(deployment.id))

    async def invoke_sync(
        self,
        deployment: AgentApiDeployment,
        input_text: str,
        tenant_id: str,
        timeout_seconds: Optional[int] = None,
        client_ip: Optional[str] = None,
        endpoint_key_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """Invoke agent synchronously via deployment (with timeout)."""
        import asyncio

        effective_timeout = timeout_seconds or deployment.timeout_seconds

        # Rate limit check
        if not deployment_router.check_rate_limit(deployment):
            return {"error": "Rate limit exceeded", "retry_after_seconds": 60}

        # Concurrency check
        if not deployment_router.acquire_concurrency(deployment):
            return {"error": "Max concurrency exceeded", "retry_after_seconds": 5}

        try:
            run = await agent_runtime.start_run(
                self.db, deployment.agent_id, tenant_id, input_text
            )

            # Poll for completion with timeout
            import time
            start = time.time()
            while time.time() - start < effective_timeout:
                await self.db.refresh(run)
                if run.status in ("completed", "failed", "cancelled"):
                    break
                await asyncio.sleep(0.5)

            if run.status == "running" or run.status == "queued":
                # Timeout
                await self._log_sla_event(deployment, "timeout", "warning", {
                    "timeout_seconds": effective_timeout,
                    "run_id": str(run.id),
                })
                return {
                    "error": "Timeout exceeded",
                    "run_id": str(run.id),
                    "status": run.status,
                    "timeout_seconds": effective_timeout,
                }

            return {
                "run_id": str(run.id),
                "status": run.status,
                "total_steps": run.total_steps,
                "total_tokens": run.total_tokens,
                "estimated_cost_brl": run.estimated_cost_brl,
            }
        except Exception as e:
            logger.exception(f"Sync deployment invoke failed: {deployment.slug}")
            return {"error": str(e)}
        finally:
            deployment_router.release_concurrency(str(deployment.id))

    async def _log_sla_event(
        self,
        deployment: AgentApiDeployment,
        event_type: str,
        severity: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        from app.models.agent_deployments import AgentApiSlaEvent
        event = AgentApiSlaEvent(
            deployment_id=deployment.id,
            tenant_id=deployment.tenant_id,
            event_type=event_type,
            severity=severity,
            details=details,
        )
        self.db.add(event)
        await self.db.flush()
