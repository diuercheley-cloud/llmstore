"""
Owner: agent-platform
Status: beta
"""

import hashlib
import logging
import uuid
from typing import Any

from app.core.config import get_settings
from app.models.agents.agents import (
    AgentBundleSignature,
    AgentBundleTrustReport,
    AgentBundleVersion,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

logger = logging.getLogger(__name__)


class AgentBundleVerifierService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    async def verify_bundle(
        self, version_id: uuid.UUID, content: bytes, is_internal: bool = False
    ) -> dict[str, Any]:
        # 1. Verify Checksum
        from sqlalchemy.orm import joinedload

        res = await self.db.execute(
            select(AgentBundleVersion)
            .options(joinedload(AgentBundleVersion.entry))
            .where(AgentBundleVersion.id == version_id)
        )
        version = res.scalar_one_or_none()
        if not version:
            return {"passed": False, "reason": "Version not found"}

        if not version.checksum_sha256:
            return {"passed": False, "reason": "Manifest checksum is missing/mandatory"}

        actual_checksum = hashlib.sha256(content).hexdigest()
        if actual_checksum != version.checksum_sha256:
            return {"passed": False, "reason": "Checksum mismatch"}

        # 2. Verify Signature if required
        res_sig = await self.db.execute(
            select(AgentBundleSignature).where(AgentBundleSignature.version_id == version_id)
        )
        signature = res_sig.scalar_one_or_none()

        is_signed = signature is not None

        # Policy enforcement
        is_prod = self.settings.app_env == "production"
        sig_required = self.settings.agent_bundle_signature_required
        internal_sig_required_in_prod = getattr(
            self.settings, "agent_internal_bundle_signature_required_in_production", True
        )
        allow_unsigned_internal = getattr(self.settings, "allow_unsigned_internal_bundles", False)

        if not is_signed:
            if not is_internal:
                return {
                    "passed": False,
                    "reason": "Signature required for external/marketplace packages",
                }

            if is_prod and internal_sig_required_in_prod:
                return {
                    "passed": False,
                    "reason": "Signature required for internal packages in production",
                }

            if not allow_unsigned_internal:
                return {
                    "passed": False,
                    "reason": "Unsigned internal bundles are blocked by policy",
                }

            logger.warning(
                "[AUDIT WARNING] Permitting unsigned internal bundle in dev/local (dev_only)."
            )

        if is_signed:
            # Mock signature verification
            expected_sig = f"sig:{actual_checksum}:{signature.public_key_id}"
            if signature.signature_value != expected_sig:
                return {"passed": False, "reason": "Invalid signature"}

        return {
            "passed": True,
            "is_signed": is_signed,
            "checksum_verified": True,
            "details": {
                "author": version.entry.author if version.entry else "unknown",
                "version": version.version,
            },
        }

    async def generate_trust_report(self, version_id: uuid.UUID) -> AgentBundleTrustReport:
        # Simple scoring logic
        res_sig = await self.db.execute(
            select(AgentBundleSignature).where(AgentBundleSignature.version_id == version_id)
        )
        is_signed = res_sig.scalar_one_or_none() is not None

        trust_score = 1.0 if is_signed else 0.5

        report = AgentBundleTrustReport(
            version_id=version_id, trust_score=trust_score, is_signed=is_signed
        )
        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)
        return report
