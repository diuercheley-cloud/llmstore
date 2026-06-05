import hashlib
import json
import logging
from typing import Any, Dict, List, Optional

from app.models.agent_marketplace import AgentAttestation, AgentPackage, AgentRevenueShare, MarketplaceItem
from app.schemas.marketplace import AgentManifest, InstallDryRunResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class MarketplaceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def validate_package(self, manifest_data: Dict[str, Any]) -> AgentManifest:
        """Validates the structure of an agent manifest."""
        return AgentManifest(**manifest_data)

    async def install_dry_run(self, manifest: AgentManifest, package_url: str) -> InstallDryRunResponse:
        """
        Performs a pre-installation check without changing system state.
        """
        warnings = []
        policy_evaluation = "allowed"
        
        # 1. Check for dangerous permissions
        dangerous_perms = ["filesystem:write", "network:outbound", "admin:all"]
        for p in manifest.permissions:
            if p in dangerous_perms:
                policy_evaluation = "needs_review"
                warnings.append(f"Dangerous permission requested: {p}")

        # 2. Attestation simulation
        attestation_verified = True
        if not manifest.signature:
            attestation_verified = False
            warnings.append("Package is unsigned and will be marked as untrusted.")

        # 3. Revenue share advisory
        estimated_revenue_share = 0.7 # Default 70%

        return InstallDryRunResponse(
            manifest=manifest,
            policy_evaluation=policy_evaluation,
            warnings=warnings,
            estimated_revenue_share=estimated_revenue_share,
            attestation_verified=attestation_verified
        )

    async def list_available_agents(self) -> List[MarketplaceItem]:
        stmt = select(MarketplaceItem).where(MarketplaceItem.is_public == True)
        res = await self.db.execute(stmt)
        return res.scalars().all()

    async def register_item(self, publisher_id: str, manifest: AgentManifest) -> MarketplaceItem:
        import uuid
        item = MarketplaceItem(
            publisher_id=uuid.UUID(publisher_id),
            name=manifest.name,
            version=manifest.version,
            category="general",
            description=manifest.description,
            manifest_json=manifest.model_dump(),
            risk_level="low" if not manifest.permissions else "medium"
        )
        self.db.add(item)
        await self.db.flush()
        return item
