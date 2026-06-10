# Owner: agent-platform
import logging
import uuid

from app.models.agents.agent_marketplace import MarketplaceDownloadEvent, MarketplaceItem
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class MarketplaceAnalyticsService:
    """
    Tracks and analyzes usage of marketplace items.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_download(self, item_id: uuid.UUID, tenant_id: str, version: str) -> MarketplaceDownloadEvent:
        event = MarketplaceDownloadEvent(
            item_id=item_id,
            tenant_id=tenant_id,
            version=version
        )
        self.db.add(event)
        
        # Update total downloads in item
        stmt = select(MarketplaceItem).where(MarketplaceItem.id == item_id)
        res = await self.db.execute(stmt)
        item = res.scalar_one_or_none()
        if item:
            item.total_downloads += 1
            
        await self.db.flush()
        return event

    async def get_download_stats(self, item_id: uuid.UUID):
        stmt = select(func.count(MarketplaceDownloadEvent.id)).where(MarketplaceDownloadEvent.item_id == item_id)
        res = await self.db.execute(stmt)
        return {"total_downloads": res.scalar_one()}
