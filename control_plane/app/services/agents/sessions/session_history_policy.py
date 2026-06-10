# Owner: agent-platform
import logging
import uuid
from datetime import timedelta
from typing import Dict, Optional

from app.core.time import utc_now
from app.models.agents.agent_sessions import (
    AgentSession,
    AgentSessionSummary,
    AgentThreadMessage,
)
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

SUMMARIZATION_MODEL = "default"
SUMMARY_TRIGGER_MESSAGE_COUNT = 50
SUMMARY_MAX_MESSAGES = 30
DEFAULT_RETENTION_DAYS = 90


class SessionHistoryPolicyService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def should_summarize(self, session_id: uuid.UUID) -> bool:
        stmt = select(func.count(AgentThreadMessage.id)).where(
            AgentThreadMessage.session_id == session_id
        )
        res = await self.db.execute(stmt)
        count = res.scalar() or 0
        return count >= SUMMARY_TRIGGER_MESSAGE_COUNT

    async def get_message_count(self, session_id: uuid.UUID) -> int:
        stmt = select(func.count(AgentThreadMessage.id)).where(
            AgentThreadMessage.session_id == session_id
        )
        res = await self.db.execute(stmt)
        return res.scalar() or 0

    async def build_summary_context(
        self, session_id: uuid.UUID
    ) -> str:
        from sqlalchemy import desc

        stmt = (
            select(AgentThreadMessage)
            .where(AgentThreadMessage.session_id == session_id)
            .order_by(desc(AgentThreadMessage.created_at))
            .limit(SUMMARY_MAX_MESSAGES)
        )
        res = await self.db.execute(stmt)
        messages = list(reversed(res.scalars().all()))

        lines = []
        for msg in messages:
            prefix = f"[{msg.role.upper()}]"
            content_preview = msg.content[:500]
            lines.append(f"{prefix}: {content_preview}")

        return "\n\n".join(lines)

    async def create_summary(
        self,
        session_id: uuid.UUID,
        summary_text: str,
        model_used: Optional[str] = None,
    ) -> AgentSessionSummary:
        msg_count = await self.get_message_count(session_id)
        summary = AgentSessionSummary(
            session_id=session_id,
            summary_text=summary_text,
            model_used=model_used or SUMMARIZATION_MODEL,
            message_count=msg_count,
        )
        self.db.add(summary)
        await self.db.flush()
        return summary

    async def get_latest_summary(
        self, session_id: uuid.UUID
    ) -> Optional[AgentSessionSummary]:
        from sqlalchemy import desc

        stmt = (
            select(AgentSessionSummary)
            .where(AgentSessionSummary.session_id == session_id)
            .order_by(desc(AgentSessionSummary.created_at))
            .limit(1)
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_retention_days(self, session: AgentSession) -> int:
        if session.retention_policy and "retention_days" in session.retention_policy:
            return int(session.retention_policy["retention_days"])
        return DEFAULT_RETENTION_DAYS

    async def apply_session_retention(
        self, session: AgentSession, dry_run: bool = False
    ) -> Dict[str, int]:
        retention_days = await self.get_retention_days(session)
        cutoff = utc_now() - timedelta(days=retention_days)
        result = {"messages_deleted": 0, "summaries_deleted": 0, "retained_summaries": 0}

        stmt_msg = select(func.count(AgentThreadMessage.id)).where(
            AgentThreadMessage.session_id == session.id,
            AgentThreadMessage.created_at < cutoff,
        )
        res = await self.db.execute(stmt_msg)
        old_messages = res.scalar() or 0
        if not isinstance(old_messages, int):
            old_messages = getattr(res, "rowcount", 0)
        if not isinstance(old_messages, int):
            old_messages = 0

        if old_messages > 0 and not dry_run:
            del_stmt = delete(AgentThreadMessage).where(
                AgentThreadMessage.session_id == session.id,
                AgentThreadMessage.created_at < cutoff,
            )
            await self.db.execute(del_stmt)
            result["messages_deleted"] = old_messages

        keep_summaries = True
        if session.retention_policy:
            keep_summaries = session.retention_policy.get("keep_summaries", True)

        if not keep_summaries:
            stmt_sum = select(func.count(AgentSessionSummary.id)).where(
                AgentSessionSummary.session_id == session.id,
                AgentSessionSummary.created_at < cutoff,
            )
            res = await self.db.execute(stmt_sum)
            old_summaries = res.scalar() or 0
            if old_summaries > 0 and not dry_run:
                del_sum = delete(AgentSessionSummary).where(
                    AgentSessionSummary.session_id == session.id,
                    AgentSessionSummary.created_at < cutoff,
                )
                await self.db.execute(del_sum)
                result["summaries_deleted"] = old_summaries
        else:
            result["retained_summaries"] = 1

        if not dry_run and (result["messages_deleted"] > 0 or result["summaries_deleted"] > 0):
            await self.db.commit()

        return result

    async def apply_retention_policies(
        self, db: AsyncSession, dry_run: bool = False
    ) -> Dict[str, int]:
        stmt = select(AgentSession).where(
            AgentSession.status.in_(["active", "archived"])
        )
        res = await db.execute(stmt)
        sessions = list(res.scalars().all())

        totals = {"sessions_processed": 0, "messages_deleted": 0, "summaries_deleted": 0}

        for session in sessions:
            result = await self.apply_session_retention(session, dry_run=dry_run)
            totals["sessions_processed"] += 1
            totals["messages_deleted"] += result["messages_deleted"]
            totals["summaries_deleted"] += result["summaries_deleted"]

        logger.info(
            f"Retention applied to {totals['sessions_processed']} sessions "
            f"(dry_run={dry_run}): {totals['messages_deleted']} messages, "
            f"{totals['summaries_deleted']} summaries deleted"
        )
        return totals
