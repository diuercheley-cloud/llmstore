# Owner: agent-platform
import uuid
import hashlib
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.agents import AgentRun
from app.models.agent_cognitive_loopback import AgentSuccessPattern

class SuccessPatternMiner:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def mine_run(self, run_id: uuid.UUID) -> Optional[AgentSuccessPattern]:
        stmt = select(AgentRun).where(AgentRun.id == run_id)
        res = await self.db.execute(stmt)
        run = res.scalar_one_or_none()
        
        if not run or run.status != "completed":
            return None
            
        # Success Criteria:
        # 1. Status is completed
        # 2. (In real implementation) No safety failures
        # 3. (In real implementation) Eval passed if available
        
        # Extract pattern
        input_text = run.input_text or ""
        fingerprint = hashlib.sha256(input_text.encode()).hexdigest()
        
        # Check if already mined
        stmt_pattern = select(AgentSuccessPattern).where(
            AgentSuccessPattern.agent_id == run.agent_id,
            AgentSuccessPattern.input_fingerprint == fingerprint
        )
        res_pattern = await self.db.execute(stmt_pattern)
        if res_pattern.scalar_one_or_none():
            return None # Already mined
            
        pattern = AgentSuccessPattern(
            agent_id=run.agent_id,
            tenant_id=run.tenant_id,
            input_fingerprint=fingerprint,
            success_reason="Autonomous completion with status 'completed'",
            tool_sequence=[] # Mock tool sequence extraction
        )
        self.db.add(pattern)
        await self.db.commit()
        await self.db.refresh(pattern)
        return pattern
