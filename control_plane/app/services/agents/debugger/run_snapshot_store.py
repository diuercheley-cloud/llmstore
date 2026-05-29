# Owner: agent-platform
import uuid
import hashlib
import json
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.agent_debugger import AgentRunSnapshot

class RunSnapshotStore:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def capture_step(self, run_id: uuid.UUID, step_number: int, data: Dict[str, Any]) -> AgentRunSnapshot:
        """
        Takes a snapshot of the current agent state at a specific step.
        """
        raw_state = data.get("state", {})
        sanitized_state = self._sanitize_state(raw_state)
        
        state_str = json.dumps(sanitized_state, sort_keys=True)
        state_hash = hashlib.sha256(state_str.encode()).hexdigest()
        
        context_hash = hashlib.sha256(json.dumps(data.get("context", {}), sort_keys=True).encode()).hexdigest()
        
        snapshot = AgentRunSnapshot(
            run_id=run_id,
            step_number=step_number,
            state_hash=state_hash,
            full_state=sanitized_state,
            memory_references=data.get("memory_refs", []),
            tool_receipts=data.get("tool_receipts", []),
            policy_decisions=data.get("policy_decisions", []),
            context_hash=context_hash
        )
        self.db.add(snapshot)
        await self.db.commit()
        await self.db.refresh(snapshot)
        return snapshot

    def _sanitize_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Removes sensitive data and masks internal reasoning (CoT) from snapshots.
        """
        import copy
        s = json.loads(json.dumps(state)) # Deep copy
        
        # Mask Chain of Thought if present
        if "chain_of_thought" in s:
            s["chain_of_thought"] = "[MASKED FOR DEBUGGER]"
        if "internal_reasoning" in s:
            s["internal_reasoning"] = "[MASKED FOR DEBUGGER]"
            
        # Basic secret masking
        def mask_secrets(obj):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if any(key in k.lower() for key in ["secret", "password", "token", "key"]):
                        obj[k] = "********"
                    else:
                        mask_secrets(v)
            elif isinstance(obj, list):
                for item in obj:
                    mask_secrets(item)
                    
        mask_secrets(s)
        return s

    async def get_snapshots(self, run_id: uuid.UUID) -> List[AgentRunSnapshot]:
        stmt = select(AgentRunSnapshot).where(AgentRunSnapshot.run_id == run_id).order_by(AgentRunSnapshot.step_number)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_snapshot_at_step(self, run_id: uuid.UUID, step_number: int) -> Optional[AgentRunSnapshot]:
        stmt = select(AgentRunSnapshot).where(
            AgentRunSnapshot.run_id == run_id, 
            AgentRunSnapshot.step_number == step_number
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()
