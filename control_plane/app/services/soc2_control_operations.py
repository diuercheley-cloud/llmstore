from datetime import datetime
from typing import Any, Dict, List

from app.models.operations.soc2 import (
    SOC2AccessReview,
    SOC2ControlException,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class SOC2ControlOperationsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_access_review(self, data: Dict[str, Any]) -> SOC2AccessReview:
        self._validate_review(data)
        review = SOC2AccessReview(**data)
        self.db.add(review)
        await self.db.commit()
        return review

    async def create_exception(self, data: Dict[str, Any]) -> SOC2ControlException:
        if not data.get("expiration_date"):
            raise ValueError("Exception must have an expiration date")
        
        exception = SOC2ControlException(**data)
        self.db.add(exception)
        await self.db.commit()
        return exception

    async def get_active_exceptions(self) -> List[SOC2ControlException]:
        result = await self.db.execute(
            select(SOC2ControlException).where(SOC2ControlException.status == "active")
        )
        return result.scalars().all()

    async def check_expired_exceptions(self) -> List[SOC2ControlException]:
        now = datetime.utcnow()
        result = await self.db.execute(
            select(SOC2ControlException).where(
                SOC2ControlException.expiration_date < now,
                SOC2ControlException.status == "active"
            )
        )
        expired = result.scalars().all()
        for e in expired:
            e.status = "expired"
        await self.db.commit()
        return expired

    def _validate_review(self, data: Dict[str, Any]):
        if not data.get("reviewer"):
            raise ValueError("Review must have a designated reviewer")
        if not data.get("owner"):
            raise ValueError("Review must have an owner")
        if data.get("remediation_actions") and not data.get("owner"):
            raise ValueError("Remediation actions require an owner responsible for execution")

    async def list_access_reviews(self) -> List[SOC2AccessReview]:
        result = await self.db.execute(select(SOC2AccessReview))
        return result.scalars().all()
