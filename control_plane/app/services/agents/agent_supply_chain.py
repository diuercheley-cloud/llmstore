"""
Owner: agent-platform
Status: beta
"""

import logging
import uuid

from app.core.time import utc_now
from app.models.agents.agents import AgentBundleProvenance, AgentPublicationReview
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

logger = logging.getLogger(__name__)


class AgentSupplyChainService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_provenance(
        self,
        version_id: uuid.UUID,
        source_url: str,
        build_id: str,
        commit_sha: str,
        builder_id: str,
    ) -> AgentBundleProvenance:
        provenance = AgentBundleProvenance(
            version_id=version_id,
            source_url=source_url,
            build_id=build_id,
            commit_sha=commit_sha,
            builder_id=builder_id,
            created_at=utc_now(),
        )
        self.db.add(provenance)
        await self.db.commit()
        await self.db.refresh(provenance)
        return provenance

    async def submit_for_review(
        self, version_id: uuid.UUID, reviewer_id: str
    ) -> AgentPublicationReview:
        review = AgentPublicationReview(
            version_id=version_id, reviewer_id=reviewer_id, status="pending", created_at=utc_now()
        )
        self.db.add(review)
        await self.db.commit()
        await self.db.refresh(review)
        return review

    async def approve_publication(self, review_id: uuid.UUID, notes: str) -> AgentPublicationReview:
        res = await self.db.execute(
            select(AgentPublicationReview).where(AgentPublicationReview.id == review_id)
        )
        review = res.scalar_one_or_none()
        if not review:
            raise ValueError("Review not found")

        review.status = "approved"
        review.review_notes = notes
        await self.db.commit()
        await self.db.refresh(review)
        return review
