import uuid

from app.core.time import utc_now
from app.models.agents.agent_catalog import PluginTrustReportGov
from sqlalchemy.ext.asyncio import AsyncSession


class TrustReportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_report(self, catalog_entry_id: uuid.UUID, trust_score: float, findings: dict):
        report = PluginTrustReportGov(
            catalog_entry_id=catalog_entry_id,
            scan_status="completed",
            trust_score=trust_score,
            findings=findings,
            last_scanned_at=utc_now()
        )
        self.db.add(report)
        await self.db.commit()
        return report
