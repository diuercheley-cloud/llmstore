import uuid
from typing import Optional

from app.core.time import utc_now
from app.models.agents.agent_workspace import (
    AgentArtifactComment,
    AgentArtifactEvent,
    AgentArtifactReview,
    AgentSharedArtifact,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select


class ArtifactReviewManager:
    @staticmethod
    async def add_review(
        db: AsyncSession,
        artifact_id: uuid.UUID,
        version_id: uuid.UUID,
        reviewer_id: str,
        reviewer_type: str,
        status: str,
        comment: Optional[str] = None
    ) -> AgentArtifactReview:
        """Adds a review/approval record for a version of an artifact."""
        if status not in ["pending", "approved", "rejected", "changes_requested"]:
            raise ValueError("Invalid review status. Must be pending, approved, rejected, or changes_requested.")

        review = AgentArtifactReview(
            artifact_id=artifact_id,
            version_id=version_id,
            reviewer_id=reviewer_id,
            reviewer_type=reviewer_type,
            status=status,
            comment=comment,
            created_at=utc_now(),
            updated_at=utc_now()
        )
        db.add(review)

        # Log event
        event = AgentArtifactEvent(
            artifact_id=artifact_id,
            event_type="reviewed",
            actor_id=reviewer_id,
            actor_type=reviewer_type,
            payload={"version_id": str(version_id), "status": status, "comment": comment},
            created_at=utc_now()
        )
        db.add(event)
        
        await db.commit()
        await db.refresh(review)
        return review

    @staticmethod
    async def check_promotion_allowed(db: AsyncSession, artifact_id: uuid.UUID, version_id: uuid.UUID) -> None:
        """Checks if there is at least one 'approved' review for this version."""
        stmt = select(AgentArtifactReview).where(
            AgentArtifactReview.artifact_id == artifact_id,
            AgentArtifactReview.version_id == version_id,
            AgentArtifactReview.status == "approved"
        )
        result = await db.execute(stmt)
        approvals = result.scalars().all()
        if not approvals:
            raise PermissionError("Artifact must have an approved review for the current version before promotion.")

    @staticmethod
    async def add_comment(
        db: AsyncSession,
        artifact_id: uuid.UUID,
        author_id: str,
        author_type: str,
        content: str,
        version_id: Optional[uuid.UUID] = None,
        parent_id: Optional[uuid.UUID] = None
    ) -> AgentArtifactComment:
        """Adds a comment on the artifact (or a specific version, or as a reply to another comment)."""
        comment = AgentArtifactComment(
            artifact_id=artifact_id,
            version_id=version_id,
            author_id=author_id,
            author_type=author_type,
            content=content,
            parent_id=parent_id,
            created_at=utc_now()
        )
        db.add(comment)

        # Log event
        event = AgentArtifactEvent(
            artifact_id=artifact_id,
            event_type="commented",
            actor_id=author_id,
            actor_type=author_type,
            payload={"version_id": str(version_id) if version_id else None, "comment_snippet": content[:100]},
            created_at=utc_now()
        )
        db.add(event)

        await db.commit()
        await db.refresh(comment)
        return comment

    @staticmethod
    async def promote_artifact(db: AsyncSession, artifact: AgentSharedArtifact, actor_id: str, actor_type: str) -> None:
        """Promotes an artifact status to 'published' after verifying reviews."""
        if not artifact.current_version_id:
            raise ValueError("Cannot promote an artifact with no versions.")

        # Enforce review required before promotion
        await ArtifactReviewManager.check_promotion_allowed(db, artifact.id, artifact.current_version_id)

        artifact.status = "published"
        
        # Log event
        event = AgentArtifactEvent(
            artifact_id=artifact.id,
            event_type="promoted",
            actor_id=actor_id,
            actor_type=actor_type,
            payload={"version_id": str(artifact.current_version_id), "status": "published"},
            created_at=utc_now()
        )
        db.add(event)
        
        await db.commit()
        await db.refresh(artifact)
