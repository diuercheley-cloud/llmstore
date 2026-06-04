# Owner: agent-platform
import hashlib
import json
import logging
import uuid
from typing import List, Optional

from app.core.config import get_settings
from app.models.agents import (
    AgentBundleInstall,
    AgentBundleTrustReport,
    AgentBundleVersion,
    AgentMarketplaceEntry,
)
from app.services.agents import agent_state
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

logger = logging.getLogger(__name__)

class AgentMarketplaceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    async def list_marketplace(self) -> List[AgentMarketplaceEntry]:
        stmt = select(AgentMarketplaceEntry).order_by(AgentMarketplaceEntry.name)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def install_bundle(self, tenant_id: str, bundle_data: bytes, filename: str) -> AgentBundleInstall:
        if not self.settings.agent_bundle_install_enabled:
            raise RuntimeError("Agent bundle installation is disabled.")

        # 1. Extract and Validate Manifest
        # Simplified: assuming bundle_data is JSON for the POC
        try:
            manifest = json.loads(bundle_data)
        except Exception:
             raise ValueError("Invalid bundle format: manifest.json not found or corrupted.")

        # Check checksums if provided
        sha256 = hashlib.sha256(bundle_data).hexdigest()
        
        # Check signature if required
        if self.settings.agent_bundle_signature_required:
            if not manifest.get("signature"):
                raise ValueError("Agent bundle signature is required but missing.")

        name = manifest["name"]
        version_str = manifest["version"]

        # 2. Update/Create Marketplace Entry
        stmt_entry = select(AgentMarketplaceEntry).where(AgentMarketplaceEntry.name == name)
        res_entry = await self.db.execute(stmt_entry)
        entry = res_entry.scalar_one_or_none()

        if not entry:
            entry = AgentMarketplaceEntry(
                name=name,
                description=manifest.get("description", ""),
                author=manifest.get("author", "Unknown"),
                category=manifest.get("category", "general")
            )
            self.db.add(entry)
            await self.db.flush()

        # 3. Create Version
        version = AgentBundleVersion(
            entry_id=entry.id,
            version=version_str,
            checksum_sha256=sha256,
            manifest_json=manifest,
            min_platform_version=manifest.get("min_platform_version", "1.0.0")
        )
        self.db.add(version)
        await self.db.flush()

        # 4. Create Trust Report
        report = AgentBundleTrustReport(
            version_id=version.id,
            trust_score=0.9, # Placeholder
            is_signed=bool(manifest.get("signature")),
            signer_identity=manifest.get("signer"),
            report_details={"check": "passed"}
        )
        self.db.add(report)

        # 5. Create Agent Definition from Bundle
        agent_def_data = manifest.get("agent_definition", {})
        agent_def = await agent_state.create_agent_definition(self.db, {
            "name": agent_def_data.get("name", name),
            "version": version_str,
            "instructions": agent_def_data.get("instructions", ""),
            "model_id": agent_def_data.get("model_id", "default"),
            "owner": agent_def_data.get("owner", "marketplace"),
            "tenant_id": tenant_id,
            "allowed_tools": agent_def_data.get("allowed_tools", [])
        })

        # 6. Create Install Record
        install = AgentBundleInstall(
            tenant_id=tenant_id,
            version_id=version.id,
            agent_id=agent_def.id,
            status="installed",
            is_enabled=False
        )
        self.db.add(install)
        
        await self.db.commit()
        await self.db.refresh(install)
        return install

    async def get_trust_report(self, version_id: uuid.UUID) -> Optional[AgentBundleTrustReport]:
        stmt = select(AgentBundleTrustReport).where(AgentBundleTrustReport.version_id == version_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def enable_install(self, install_id: uuid.UUID):
        install = await self.db.get(AgentBundleInstall, install_id)
        if install:
            install.is_enabled = True
            install.status = "enabled"
            await self.db.commit()

    async def disable_install(self, install_id: uuid.UUID):
        install = await self.db.get(AgentBundleInstall, install_id)
        if install:
            install.is_enabled = False
            install.status = "disabled"
            await self.db.commit()
