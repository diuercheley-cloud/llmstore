# Owner: agent-platform
import logging
import uuid

from app.models.agents.agent_marketplace import MarketplaceItem, MarketplaceRating
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class MarketplaceRatingService:
    """
    Manages user ratings and reviews for marketplace items.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_rating(
        self, item_id: uuid.UUID, user_id: str, rating: int, review: str = None
    ) -> MarketplaceRating:
        if not (1 <= rating <= 5):
            raise ValueError("Rating must be between 1 and 5")

        # Check if user already rated
        stmt = select(MarketplaceRating).where(
            MarketplaceRating.item_id == item_id, MarketplaceRating.user_id == user_id
        )
        res = await self.db.execute(stmt)
        existing = res.scalar_one_or_none()

        if existing:
            existing.rating = rating
            existing.review = review
            rating_obj = existing
        else:
            rating_obj = MarketplaceRating(
                item_id=item_id, user_id=user_id, rating=rating, review=review
            )
            self.db.add(rating_obj)

        await self.db.flush()
        await self._update_item_aggregates(item_id)
        return rating_obj

    async def _update_item_aggregates(self, item_id: uuid.UUID):
        stmt = select(
            func.avg(MarketplaceRating.rating).label("avg"),
            func.count(MarketplaceRating.id).label("count"),
        ).where(MarketplaceRating.item_id == item_id)

        res = await self.db.execute(stmt)
        row = res.one()
        avg_val = row[0] if hasattr(row, "__getitem__") else getattr(row, "avg", None)
        count_val = row[1] if hasattr(row, "__getitem__") else getattr(row, "count", None)

        stmt_item = select(MarketplaceItem).where(MarketplaceItem.id == item_id)
        res_item = await self.db.execute(stmt_item)
        item = res_item.scalar_one_or_none()

        if item:
            item.avg_rating = float(avg_val or 0.0)
            item.total_ratings = int(count_val or 0)
            await self.db.flush()
