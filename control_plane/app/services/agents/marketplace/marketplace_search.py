# Owner: agent-platform
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_

from app.models.agent_marketplace import MarketplaceItem

logger = logging.getLogger(__name__)

class MarketplaceSearchService:
    """
    Handles discovery and search for marketplace items.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def search(
        self, 
        query: Optional[str] = None, 
        category: Optional[str] = None, 
        tags: Optional[List[str]] = None,
        capabilities: Optional[List[str]] = None,
        risk_level: Optional[str] = None,
        min_rating: float = 0.0
    ) -> List[MarketplaceItem]:
        """
        Searches marketplace items based on multiple filters.
        """
        stmt = select(MarketplaceItem).where(MarketplaceItem.is_public == True)
        
        if query:
            stmt = stmt.where(or_(
                MarketplaceItem.name.ilike(f"%{query}%"),
                MarketplaceItem.category.ilike(f"%{query}%")
            ))
            
        if category:
            stmt = stmt.where(MarketplaceItem.category == category)
            
        if risk_level:
            stmt = stmt.where(MarketplaceItem.risk_level == risk_level)
            
        if min_rating > 0:
            stmt = stmt.where(MarketplaceItem.avg_rating >= min_rating)
            
        res = await self.db.execute(stmt)
        items = list(res.scalars().all())
        
        if tags:
            items = [item for item in items if all(tag in item.tags for tag in tags)]
            
        if capabilities:
            items = [item for item in items if all(cap in item.capabilities for cap in capabilities)]
            
        return items
