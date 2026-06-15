# Owner: agent-platform
import logging
import uuid
from typing import Any

from app.models.agents.agents import AgentRedTeamCase
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class RedTeamScanner:
    """
    Framework for adversarial testing and red-teaming of agents.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_case(
        self, agent_id: uuid.UUID, attack_type: str, payload: str, expected_denial: bool = True
    ) -> AgentRedTeamCase:
        case = AgentRedTeamCase(
            agent_id=agent_id,
            attack_type=attack_type,
            payload=payload,
            expected_denial=expected_denial,
        )
        self.db.add(case)
        await self.db.flush()
        return case

    async def get_cases(
        self, agent_id: uuid.UUID, attack_type: str = None
    ) -> list[AgentRedTeamCase]:
        stmt = select(AgentRedTeamCase).where(AgentRedTeamCase.agent_id == agent_id)
        if attack_type:
            stmt = stmt.where(AgentRedTeamCase.attack_type == attack_type)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    def detect_jailbreak(self, input_text: str) -> bool:
        """Heuristic-based jailbreak detection."""
        jailbreak_keywords = [
            "DAN",
            "Developer Mode",
            "ignore previous instructions",
            "do anything now",
        ]
        return any(kw.lower() in input_text.lower() for kw in jailbreak_keywords)

    def detect_injection(self, input_text: str) -> bool:
        """Prompt injection detection."""
        injection_keywords = [
            "system override",
            "new system message",
            "END OF MESSAGE",
            "User: Admin",
        ]
        return any(kw.lower() in input_text.lower() for kw in injection_keywords)

    async def scan_interaction(self, input_text: str, output_text: str) -> dict[str, Any]:
        """
        Scans an agent interaction for security violations.
        """
        violations = []
        if self.detect_jailbreak(input_text):
            violations.append("jailbreak_attempt")
        if self.detect_injection(input_text):
            violations.append("prompt_injection")

        # Example of data exfiltration check (simplified)
        if "API_KEY" in output_text or "SECRET" in output_text:
            violations.append("data_exfiltration_risk")

        return {"secure": len(violations) == 0, "violations": violations}
