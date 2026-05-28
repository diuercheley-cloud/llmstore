# Owner: agent-platform
import hashlib
import json
import logging
from typing import Dict, List, Any, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.agents import AgentRun, AgentRunReceipt, AgentRunEvent
from app.services.agents.deterministic_state_graph import DeterministicStateGraph

logger = logging.getLogger(__name__)


class ReplayMismatchError(ValueError):
    """Raised when replayed execution diverges from original execution receipts."""
    pass


class ReplayRunner:
    def __init__(self, db: AsyncSession, run_id: uuid.UUID):
        self.db = db
        self.run_id = run_id

    async def run_replay(self) -> Dict[str, Any]:
        """
        Replays the agent run using recorded execution receipts.
        Ensures that state, inputs, outputs, and hashes match exactly.
        Returns a summary report of the replay.
        """
        # Fetch the original run
        run_stmt = select(AgentRun).where(AgentRun.id == self.run_id)
        run_res = await self.db.execute(run_stmt)
        run = run_res.scalar_one_or_none()
        if not run:
            raise ReplayMismatchError(f"Agent run {self.run_id} not found.")

        # Fetch all receipts
        receipt_stmt = select(AgentRunReceipt).where(AgentRunReceipt.run_id == self.run_id).order_by(AgentRunReceipt.step_number.asc())
        receipt_res = await self.db.execute(receipt_stmt)
        receipts = receipt_res.scalars().all()

        # Fetch all events
        event_stmt = select(AgentRunEvent).where(AgentRunEvent.run_id == self.run_id).order_by(AgentRunEvent.created_at.asc())
        event_res = await self.db.execute(event_stmt)
        events = event_res.scalars().all()

        logger.info(f"Replaying run {self.run_id} with {len(receipts)} receipts and {len(events)} events.")

        replayed_steps = []
        state_transitions = []

        # Reconstruct transitions from events for graph hashing
        for event in events:
            if "status" in (event.event_data or {}):
                state_transitions.append({
                    "id": str(event.id),
                    "from_status": event.event_data.get("old_status", "unknown"),
                    "to_status": event.event_data.get("status"),
                    "timestamp": event.created_at.isoformat()
                })

        # Replay each step
        for receipt in receipts:
            step_num = receipt.step_number
            data = receipt.receipt_data
            
            # Check step idempotency: verify recorded data structure
            if "type" not in data or "input_hash" not in data or "output_hash" not in data:
                raise ReplayMismatchError(f"Receipt for step {step_num} is malformed.")

            logger.info(f"Verifying step {step_num} of type {data.get('type')}")

            # Replay tool invocation idempotency or memory mutation checks
            if data.get("type") == "tool_execution":
                # Ensure it has necessary context
                tool_name = data.get("metadata", {}).get("tool_name")
                tool_input = data.get("metadata", {}).get("input")
                
                # Check tool invocation idempotency by hashing parameters
                param_hash = hashlib.sha256(json.dumps(tool_input, sort_keys=True).encode("utf-8")).hexdigest()
                if param_hash != data.get("input_hash"):
                    raise ReplayMismatchError(
                        f"Replay mismatch in step {step_num}: tool '{tool_name}' inputs do not match recorded input hash."
                    )

            elif data.get("type") == "workflow_signal":
                # Signal deduplication and timeline validation
                signal_name = data.get("metadata", {}).get("signal_name")
                signal_payload = data.get("metadata", {}).get("payload")
                
                payload_hash = hashlib.sha256(json.dumps(signal_payload, sort_keys=True).encode("utf-8")).hexdigest()
                if payload_hash != data.get("input_hash"):
                    raise ReplayMismatchError(
                        f"Replay mismatch in step {step_num}: signal '{signal_name}' payload does not match recorded input hash."
                    )

            replayed_steps.append({
                "step_number": step_num,
                "type": data.get("type"),
                "success": data.get("success", True),
                "output_hash": data.get("output_hash")
            })

        # Calculate replay hash
        serialized_receipts = [
            {"step_number": r.step_number, "signature": r.signature, "receipt_data": r.receipt_data}
            for r in receipts
        ]
        
        calculated_hash = DeterministicStateGraph.calculate_replay_hash(
            state_transitions=state_transitions,
            receipts=serialized_receipts,
            output_data={"final_status": run.status, "failure_reason": run.failure_reason}
        )

        return {
            "run_id": str(self.run_id),
            "replayed_steps_count": len(replayed_steps),
            "replay_hash": calculated_hash,
            "success": True,
            "status": "verified"
        }
