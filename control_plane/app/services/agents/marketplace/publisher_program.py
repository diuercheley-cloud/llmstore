# Owner: agent-platform
import logging
import uuid
from typing import Optional

from app.models.agent_marketplace import MarketplacePublisher
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class PublisherProgramService:
    """
    Manages the publisher program and verification process.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_publisher(self, tenant_id: str, name: str, description: str = None) -> MarketplacePublisher:
        publisher = MarketplacePublisher(
            tenant_id=tenant_id,
            name=name,
            description=description
        )
        self.db.add(publisher)
        await self.db.flush()
        return publisher

    async def verify_publisher(self, publisher_id: uuid.UUID, trust_score: float = 1.0):
        stmt = select(MarketplacePublisher).where(MarketplacePublisher.id == publisher_id)
        res = await self.db.execute(stmt)
        publisher = res.scalar_one_or_none()
        if publisher:
            publisher.is_verified = True
            publisher.trust_score = trust_score
            await self.db.flush()

    async def get_publisher(self, tenant_id: str) -> Optional[MarketplacePublisher]:
        stmt = select(MarketplacePublisher).where(MarketplacePublisher.tenant_id == tenant_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()
