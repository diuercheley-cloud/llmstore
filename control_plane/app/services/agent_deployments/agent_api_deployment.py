# Owner: agent-platform
import uuid
import secrets
import hashlib
import logging
from typing import Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_deployments import AgentApiDeployment, AgentApiEndpointKey
from app.models.agents import AgentDefinition
from app.core.time import utc_now
from app.core.security import hash_secret

logger = logging.getLogger(__name__)


class DeploymentError(Exception):
    pass


class DeploymentNotFoundError(DeploymentError):
    pass


class DeploymentValidationError(DeploymentError):
    pass


class AgentApiDeploymentService:
    """Manages the lifecycle of agent API deployments."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_deployment(
        self,
        tenant_id: str,
        agent_id: uuid.UUID,
        slug: str,
        name: str,
        description: Optional[str] = None,
        timeout_seconds: int = 30,
        max_concurrency: int = 10,
        rate_limit_per_minute: int = 60,
        rate_limit_per_day: int = 10000,
        retry_max_attempts: int = 0,
        callback_url: Optional[str] = None,
        billing_tier: str = "free",
    ) -> AgentApiDeployment:
        # Validate agent exists and is deployable
        agent = await self.db.get(AgentDefinition, agent_id)
        if not agent:
            raise DeploymentValidationError("Agent not found")
        if agent.tenant_id != tenant_id:
            raise DeploymentValidationError("Agent belongs to another tenant")
        if agent.status not in ("active", "approved"):
            raise DeploymentValidationError(
                f"Agent must be active or approved to deploy (current: {agent.status})"
            )

        # Validate slug uniqueness
        existing = await self._get_deployment_by_slug(slug)
        if existing:
            raise DeploymentValidationError(f"Slug '{slug}' is already taken")

        # Validate slug format
        import re
        if not re.match(r'^[a-z0-9][a-z0-9\-]{1,62}[a-z0-9]$', slug):
            raise DeploymentValidationError(
                "Slug must be 3-64 chars, lowercase alphanumeric and hyphens, "
                "starting and ending with alphanumeric"
            )

        deployment = AgentApiDeployment(
            tenant_id=tenant_id,
            agent_id=agent_id,
            slug=slug,
            name=name,
            description=description,
            timeout_seconds=timeout_seconds,
            max_concurrency=max_concurrency,
            rate_limit_per_minute=rate_limit_per_minute,
            rate_limit_per_day=rate_limit_per_day,
            retry_max_attempts=retry_max_attempts,
            callback_url=callback_url,
            billing_tier=billing_tier,
            status="active",
        )
        self.db.add(deployment)
        await self.db.flush()

        # Create default endpoint key
        await self.create_endpoint_key(deployment.id, tenant_id, "default")

        logger.info(f"Deployment created: {slug} for agent {agent_id}")
        return deployment

    async def get_deployment(self, deployment_id: uuid.UUID) -> Optional[AgentApiDeployment]:
        return await self.db.get(AgentApiDeployment, deployment_id)

    async def _get_deployment_by_slug(self, slug: str) -> Optional[AgentApiDeployment]:
        stmt = select(AgentApiDeployment).where(AgentApiDeployment.slug == slug)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_deployment_by_slug(self, slug: str, tenant_id: str) -> Optional[AgentApiDeployment]:
        stmt = select(AgentApiDeployment).where(
            AgentApiDeployment.slug == slug,
            AgentApiDeployment.tenant_id == tenant_id,
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_deployments(self, tenant_id: str, include_archived: bool = False) -> list[AgentApiDeployment]:
        stmt = select(AgentApiDeployment).where(AgentApiDeployment.tenant_id == tenant_id)
        if not include_archived:
            stmt = stmt.where(AgentApiDeployment.status != "archived")
        stmt = stmt.order_by(AgentApiDeployment.created_at.desc())
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def pause_deployment(self, deployment_id: uuid.UUID, tenant_id: str) -> AgentApiDeployment:
        deployment = await self.get_deployment(deployment_id)
        if not deployment or deployment.tenant_id != tenant_id:
            raise DeploymentNotFoundError("Deployment not found")
        deployment.status = "paused"
        await self.db.flush()
        return deployment

    async def resume_deployment(self, deployment_id: uuid.UUID, tenant_id: str) -> AgentApiDeployment:
        deployment = await self.get_deployment(deployment_id)
        if not deployment or deployment.tenant_id != tenant_id:
            raise DeploymentNotFoundError("Deployment not found")
        deployment.status = "active"
        await self.db.flush()
        return deployment

    async def archive_deployment(self, deployment_id: uuid.UUID, tenant_id: str) -> AgentApiDeployment:
        deployment = await self.get_deployment(deployment_id)
        if not deployment or deployment.tenant_id != tenant_id:
            raise DeploymentNotFoundError("Deployment not found")
        deployment.status = "archived"
        deployment.archived_at = utc_now()
        await self.db.flush()
        return deployment

    async def rollback_deployment(
        self, deployment_id: uuid.UUID, tenant_id: str, target_version_slug: str
    ) -> AgentApiDeployment:
        """Rollback to a previous deployment version's configuration."""
        deployment = await self.get_deployment(deployment_id)
        if not deployment or deployment.tenant_id != tenant_id:
            raise DeploymentNotFoundError("Deployment not found")

        target = await self._get_deployment_by_slug(target_version_slug)
        if not target or target.tenant_id != tenant_id:
            raise DeploymentNotFoundError("Target version not found")

        # Update current deployment with target's configuration
        # We keep our OWN slug but point to the target's agent and SLA
        deployment.previous_version_slug = deployment.slug # Not very useful if we don't change slug, but keeping for audit
        deployment.agent_id = target.agent_id
        deployment.version = target.version
        deployment.timeout_seconds = target.timeout_seconds
        deployment.max_concurrency = target.max_concurrency
        deployment.rate_limit_per_minute = target.rate_limit_per_minute
        deployment.rate_limit_per_day = target.rate_limit_per_day
        
        await self.db.flush()
        return deployment

    async def create_endpoint_key(
        self,
        deployment_id: uuid.UUID,
        tenant_id: str,
        name: str,
    ) -> tuple[AgentApiEndpointKey, str]:
        """Create an API key for a deployment. Returns (key_model, raw_key)."""
        raw_key = f"ak_dep_{secrets.token_urlsafe(32)}"
        key_prefix = raw_key[:12]
        key_hash = hash_secret(raw_key)

        key = AgentApiEndpointKey(
            deployment_id=deployment_id,
            tenant_id=tenant_id,
            key_prefix=key_prefix,
            key_hash=key_hash,
            name=name,
        )
        self.db.add(key)
        await self.db.flush()
        return key, raw_key

    async def validate_endpoint_key(
        self, raw_key: str, deployment_slug: str
    ) -> Optional[tuple[AgentApiDeployment, AgentApiEndpointKey]]:
        """Validate an endpoint key against a deployment slug. Returns (deployment, key) or None."""
        prefix = raw_key[:12]

        # Find key by prefix
        stmt = select(AgentApiEndpointKey).where(
            AgentApiEndpointKey.key_prefix == prefix,
            AgentApiEndpointKey.is_active == True,
        )
        res = await self.db.execute(stmt)
        key = res.scalar_one_or_none()
        if not key:
            return None

        # Verify hash
        from app.core.security import verify_secret
        if not verify_secret(raw_key, key.key_hash):
            return None

        # Check expiration
        if key.expires_at and key.expires_at < utc_now():
            return None

        # Get deployment
        deployment = await self.db.get(AgentApiDeployment, key.deployment_id)
        if not deployment or deployment.slug != deployment_slug:
            return None
        if deployment.status != "active":
            return None

        # Update last used
        key.last_used_at = utc_now()
        await self.db.flush()

        return deployment, key

    async def update_deployment(
        self,
        deployment_id: uuid.UUID,
        tenant_id: str,
        **kwargs,
    ) -> AgentApiDeployment:
        deployment = await self.get_deployment(deployment_id)
        if not deployment or deployment.tenant_id != tenant_id:
            raise DeploymentNotFoundError("Deployment not found")

        allowed_fields = {
            "name", "description", "timeout_seconds", "max_concurrency",
            "rate_limit_per_minute", "rate_limit_per_day", "retry_max_attempts",
            "retry_backoff_ms", "callback_url", "billing_tier",
        }
        for key, value in kwargs.items():
            if key in allowed_fields and value is not None:
                setattr(deployment, key, value)

        await self.db.flush()
        return deployment
