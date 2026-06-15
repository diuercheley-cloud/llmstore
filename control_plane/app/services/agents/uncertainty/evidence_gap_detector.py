# Owner: agent-platform
import uuid
from typing import Any

from app.models.agents.agent_uncertainty import AgentEvidenceGap
from sqlalchemy.ext.asyncio import AsyncSession


class EvidenceGapDetector:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def detect(self, run_id: uuid.UUID, metrics: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Identifies missing information or inconsistencies that contribute to low confidence.
        """
        gaps = []

        if metrics.get("evidence_score", 1.0) < 0.3:
            gaps.append(
                {
                    "missing_information": "Critical lack of evidentiary support for the query.",
                    "suggested_tool": "web_search",
                }
            )

        if metrics.get("contradiction_score", 0.0) > 0.4:
            gaps.append(
                {
                    "missing_information": "High level of contradiction between tool results detected.",
                    "suggested_tool": "deep_reasoning",
                }
            )

        # Persist gaps
        for gap in gaps:
            record = AgentEvidenceGap(
                run_id=run_id,
                missing_information=gap["missing_information"],
                suggested_tool=gap.get("suggested_tool"),
            )
            self.db.add(record)

        await self.db.commit()
        return gaps
