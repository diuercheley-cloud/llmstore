"""
Owner: agent-platform
Status: beta
"""
import uuid
import logging
import hashlib
from typing import Dict, Any, Optional, List
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.agents import AgentBundleVersion, AgentBundleSignature, AgentBundleTrustReport
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class AgentBundleVerifierService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    async def verify_bundle(self, version_id: uuid.UUID, content: bytes) -> Dict[str, Any]:
        # 1. Verify Checksum
        res = await self.db.execute(select(AgentBundleVersion).where(AgentBundleVersion.id == version_id))
        version = res.scalar_one_or_none()
        if not version:
             return {"passed": False, "reason": "Version not found"}

        actual_checksum = hashlib.sha256(content).hexdigest()
        if actual_checksum != version.checksum_sha256:
             return {"passed": False, "reason": "Checksum mismatch"}

        # 2. Verify Signature if required
        res_sig = await self.db.execute(select(AgentBundleSignature).where(AgentBundleSignature.version_id == version_id))
        signature = res_sig.scalar_one_or_none()
        
        is_signed = signature is not None
        if self.settings.agent_bundle_signature_required and not is_signed:
             return {"passed": False, "reason": "Signature required but missing"}

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
                "version": version.version
            }
        }

    async def generate_trust_report(self, version_id: uuid.UUID) -> AgentBundleTrustReport:
        # Simple scoring logic
        res_sig = await self.db.execute(select(AgentBundleSignature).where(AgentBundleSignature.version_id == version_id))
        is_signed = res_sig.scalar_one_or_none() is not None
        
        trust_score = 1.0 if is_signed else 0.5
        
        report = AgentBundleTrustReport(
            version_id=version_id,
            trust_score=trust_score,
            is_signed=is_signed
        )
        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)
        return report
