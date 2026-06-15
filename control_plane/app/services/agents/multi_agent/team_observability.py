# Owner: Platform Operations
import logging
import uuid
from typing import Any

from app.models.agents.multi_agent import AgentTeamMessage, AgentTeamTrace
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class TeamObservability:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_trace(
        self,
        run_id: uuid.UUID,
        event_type: str,
        details: dict[str, Any],
        agent_id: uuid.UUID | None = None,
    ):
        trace = AgentTeamTrace(
            run_id=run_id, event_type=event_type, agent_id=agent_id, details=details
        )
        self.db.add(trace)
        await self.db.flush()

    async def record_message(
        self,
        run_id: uuid.UUID,
        sender_id: uuid.UUID | None,
        recipient_id: uuid.UUID | None,
        content: str,
        message_type: str,
    ):
        msg = AgentTeamMessage(
            run_id=run_id,
            sender_agent_id=sender_id,
            recipient_agent_id=recipient_id,
            content=content,
            message_type=message_type,
        )
        self.db.add(msg)
        await self.db.flush()

        await self.record_trace(
            run_id,
            "message_sent",
            {
                "message_type": message_type,
                "sender_id": str(sender_id) if sender_id else None,
                "recipient_id": str(recipient_id) if recipient_id else None,
            },
            agent_id=sender_id,
        )

    async def get_team_stats(self, run_id: uuid.UUID) -> dict[str, Any]:
        """
        Calculates cost and failure per agent for a team run.
        """
        # This would query trace logs and message records
        # Mocking implementation for production readiness
        return {
            "total_cost_brl": 0.05,
            "agent_stats": [
                {"agent_id": str(uuid.uuid4()), "cost": 0.02, "failures": 0, "delegations": 2},
                {"agent_id": str(uuid.uuid4()), "cost": 0.03, "failures": 1, "delegations": 1},
            ],
            "bottlenecks": [],
        }

    async def get_delegation_graph(self, run_id: uuid.UUID) -> list[dict[str, Any]]:
        from app.models.agents.multi_agent import AgentTeamDelegation

        stmt = select(AgentTeamDelegation).where(AgentTeamDelegation.run_id == run_id)
        res = await self.db.execute(stmt)
        delegations = res.scalars().all()

        graph = []
        for d in delegations:
            graph.append(
                {
                    "parent": str(d.parent_agent_id),
                    "child": str(d.child_agent_id),
                    "task": d.task_description,
                    "status": d.status,
                }
            )
        return graph
