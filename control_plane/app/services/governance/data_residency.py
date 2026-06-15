"""
Data Residency enforcement for multi-region deployments.
Ensures tenant data is stored and processed in approved regions only.
"""

import logging
from dataclasses import dataclass, field

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class ResidencyPolicy:
    tenant_id: str
    allowed_regions: set[str] = field(default_factory=set)
    prohibited_regions: set[str] = field(default_factory=set)
    data_classification: str = "internal"  # public, internal, confidential, restricted
    require_sovereign_processing: bool = False
    allow_cross_region_backup: bool = False
    backup_region: str | None = None

    def is_allowed(self, region: str) -> bool:
        if self.prohibited_regions and region in self.prohibited_regions:
            return False
        if self.allowed_regions and region not in self.allowed_regions:
            return False
        return True


class DataResidencyService:
    """
    Enforces data residency policies per tenant.
    Validates that agent data, memory, and processing stay within approved regions.
    """

    def __init__(self):
        self.settings = get_settings()
        self._policies: dict[str, ResidencyPolicy] = {}
        self._current_region = self.settings.cluster_region or "default"

    def configure_policy(self, policy: ResidencyPolicy):
        self._policies[policy.tenant_id] = policy
        logger.info(
            "Residency policy configured for tenant %s: %s",
            policy.tenant_id,
            policy.allowed_regions,
        )

    def get_policy(self, tenant_id: str) -> ResidencyPolicy | None:
        return self._policies.get(tenant_id)

    def validate_storage(
        self, tenant_id: str, data_classification: str, target_region: str | None = None
    ) -> bool:
        policy = self._policies.get(tenant_id)
        if not policy:
            return True

        region = target_region or self._current_region
        if data_classification == "restricted" and policy.require_sovereign_processing:
            if region != self._current_region:
                logger.warning(
                    "Restricted data for tenant %s requires sovereign processing in %s",
                    tenant_id,
                    region,
                )
                return False

        if not policy.is_allowed(region):
            logger.warning(
                "Region %s not allowed for tenant %s data (allowed: %s)",
                region,
                tenant_id,
                policy.allowed_regions,
            )
            return False

        return True

    def validate_backup(self, tenant_id: str, target_region: str) -> bool:
        policy = self._policies.get(tenant_id)
        if not policy:
            return True

        if not policy.allow_cross_region_backup:
            logger.warning("Cross-region backup not allowed for tenant %s", tenant_id)
            return False

        if policy.backup_region and target_region != policy.backup_region:
            logger.warning(
                "Backup region %s != configured backup region %s for tenant %s",
                target_region,
                policy.backup_region,
                tenant_id,
            )
            return False

        return True

    def filter_allowed_regions(self, tenant_id: str, regions: list[str]) -> list[str]:
        policy = self._policies.get(tenant_id)
        if not policy:
            return regions

        return [r for r in regions if policy.is_allowed(r)]

    def get_restricted_tenants(self) -> list[str]:
        return [
            tid
            for tid, p in self._policies.items()
            if p.data_classification in ("confidential", "restricted")
        ]


class DataResidencyMiddleware:
    """
    Middleware to enforce data residency on API requests.
    Checks X-Tenant-ID and X-Region headers against configured policies.
    """

    def __init__(self, residency_service: DataResidencyService):
        self.service = residency_service

    async def check_request(self, tenant_id: str, request_region: str | None = None) -> bool:
        region = request_region or self.service._current_region
        return self.service.validate_storage(tenant_id, "internal", region)

    async def check_agent_memory(
        self, tenant_id: str, memory_data_classification: str = "internal"
    ) -> bool:
        return self.service.validate_storage(tenant_id, memory_data_classification)

    async def check_agent_run(self, tenant_id: str, agent_id: str) -> bool:
        return self.service.validate_storage(tenant_id, "internal")
