import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from sqlalchemy.orm import selectinload

from app.models.operations.compliance import (
    ComplianceFramework,
    ComplianceControl,
    ComplianceEvidenceItem,
    ComplianceControlTest,
    ComplianceRiskItem,
    CompliancePolicyDocument,
)

class ComplianceReadinessService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_frameworks(self) -> List[ComplianceFramework]:
        result = await self.db.execute(select(ComplianceFramework))
        return result.scalars().all()

    async def get_readiness_report(self, framework_id: str) -> Dict[str, Any]:
        framework = await self.db.get(ComplianceFramework, framework_id, options=[selectinload(ComplianceFramework.controls)])
        if not framework:
            raise ValueError("Framework not found")

        total_controls = len(framework.controls)
        implemented = len([c for c in framework.controls if c.status == "implemented"])
        partial = len([c for c in framework.controls if c.status == "partial"])
        
        readiness_score = (implemented + (partial * 0.5)) / total_controls if total_controls > 0 else 0

        return {
            "framework": framework.name,
            "readiness_score": readiness_score,
            "controls_summary": {
                "total": total_controls,
                "implemented": implemented,
                "partial": partial,
                "not_started": total_controls - implemented - partial
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    async def seed_frameworks(self):
        # SOC 2
        soc2 = await self.db.execute(select(ComplianceFramework).where(ComplianceFramework.name == "SOC2"))
        if not soc2.scalars().first():
            f = ComplianceFramework(
                name="SOC2",
                description="Trust Services Criteria: Security, Availability, Processing Integrity, Confidentiality, and Privacy.",
                version="2017"
            )
            self.db.add(f)
            await self.db.flush()
            
            # Add some core controls
            controls = [
                ComplianceControl(framework_id=f.id, code="CC1.1", title="Ethics and Integrity", category="Security"),
                ComplianceControl(framework_id=f.id, code="CC6.1", title="Logical Access Security", category="Security"),
                ComplianceControl(framework_id=f.id, code="CC7.1", title="System Operations Monitoring", category="Security"),
            ]
            self.db.add_all(controls)

        # ISO 27001
        iso = await self.db.execute(select(ComplianceFramework).where(ComplianceFramework.name == "ISO27001"))
        if not iso.scalars().first():
            f = ComplianceFramework(
                name="ISO27001",
                description="Information Security Management Systems requirements.",
                version="2022"
            )
            self.db.add(f)
            await self.db.flush()
            
            controls = [
                ComplianceControl(framework_id=f.id, code="A.5.1", title="Policies for information security", category="Governance"),
                ComplianceControl(framework_id=f.id, code="A.9.1", title="Access control policy", category="Access Control"),
            ]
            self.db.add_all(controls)

        await self.db.commit()

    async def collect_evidence(self, control_id: str, name: str, description: str, content: str):
        # Safety Check: Scan for secrets in content
        if "PRIVATE KEY" in content or "API_KEY" in content:
            raise ValueError("Evidence contains sensitive information (secrets detected)")
            
        evidence = ComplianceEvidenceItem(
            control_id=control_id,
            name=name,
            description=description,
            source_type="auto_script",
            content_reference=content # In production, this would be a hash or file path
        )
        self.db.add(evidence)
        
        # Update control status to partial if it was not_started
        control = await self.db.get(ComplianceControl, control_id)
        if control and control.status == "not_started":
            control.status = "partial"
            
        await self.db.commit()
        return evidence
