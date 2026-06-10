import logging
import uuid
from typing import Any, Dict, List, Optional

from app.models.agents.agent_marketplace import MarketplaceItem
from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class MarketplaceSearchService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def search(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        capabilities: Optional[List[str]] = None,
        risk_level: Optional[str] = None,
        min_rating: float = 0.0,
        publisher_id: Optional[uuid.UUID] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        limit: int = 20,
        offset: int = 0,
    ) -> Dict[str, Any]:
        stmt = select(MarketplaceItem).where(MarketplaceItem.is_public == True)

        if query:
            stmt = stmt.where(or_(
                MarketplaceItem.name.ilike(f"%{query}%"),
                MarketplaceItem.category.ilike(f"%{query}%"),
                MarketplaceItem.tags[query].as_string().ilike(f"%{query}%"),
            ))

        if category:
            stmt = stmt.where(MarketplaceItem.category == category)

        if risk_level:
            stmt = stmt.where(MarketplaceItem.risk_level == risk_level)

        if min_rating > 0:
            stmt = stmt.where(MarketplaceItem.avg_rating >= min_rating)

        if publisher_id:
            stmt = stmt.where(MarketplaceItem.publisher_id == publisher_id)

        # Count total before pagination
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_res = await self.db.execute(count_stmt)
        total = total_res.scalar_one()

        # Apply sorting
        sort_col = getattr(MarketplaceItem, sort_by, MarketplaceItem.created_at)
        order_fn = desc if sort_order == "desc" else asc
        stmt = stmt.order_by(order_fn(sort_col))

        # Apply pagination
        stmt = stmt.offset(offset).limit(limit)

        res = await self.db.execute(stmt)
        items = list(res.scalars().all())

        # In-memory filters for JSON array fields
        if tags:
            items = [item for item in items if all(tag in (item.tags or []) for tag in tags)]

        if capabilities:
            items = [item for item in items if all(cap in (item.capabilities or []) for cap in capabilities)]

        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    async def get_categories(self) -> List[str]:
        stmt = select(MarketplaceItem.category).where(MarketplaceItem.is_public == True).distinct()
        res = await self.db.execute(stmt)
        return [row[0] for row in res.all() if row[0]]

    async def get_item(self, item_id: uuid.UUID) -> Optional[MarketplaceItem]:
        stmt = select(MarketplaceItem).where(
            MarketplaceItem.id == item_id,
            MarketplaceItem.is_public == True,
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()
