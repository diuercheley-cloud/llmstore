import uuid
import time
import logging
from typing import Any, Dict, Optional, List, Callable
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_settings
from app.core.time import utc_now
from app.services.agents import agent_state
from app.services.agents.agent_observability import AgentObservabilityService
from app.services.agents.agent_memory import AgentMemoryService
from app.services.agents.agent_policy_engine import AgentPolicyEngine, PolicyDecision
from app.services.agents.agent_handoffs import AgentHandoffService

logger = logging.getLogger(__name__)

class MockLLMProvider:
    """Mock LLM Provider for testing agent executions."""
    def __init__(self, responses: Optional[List[Dict[str, Any]]] = None):
        # List of predefined responses. Each response can decide next step:
        # e.g., {"type": "tool_call", "tool_name": "calculator", "tool_input": {"expression": "2+2"}}
        # or {"type": "final", "output": "The result is 4"}
        self.responses = responses or []
        self.current_idx = 0

    async def generate(self, prompt_hash: str, system_instructions_hash: str, allowed_tools: List[str]) -> Dict[str, Any]:
        if self.current_idx < len(self.responses):
            res = self.responses[self.current_idx]
            self.current_idx += 1
            return res
        # Default fallback response
        return {"type": "final", "output": "Default mock response"}


class AgentExecutor:
    def __init__(
        self,
        db: AsyncSession,
        run_id: uuid.UUID,
        llm_provider: Optional[Any] = None,
        tool_runner: Optional[Callable[[str, Any], Any]] = None,
    ):
        self.db = db
        self.run_id = run_id
        self.settings = get_settings()
        self.llm_provider = llm_provider or MockLLMProvider()
        self.tool_runner = tool_runner
        self.obs = AgentObservabilityService()
        self.memory = AgentMemoryService(db)
        self.policy_engine = AgentPolicyEngine(db)
        self.handoff = AgentHandoffService(db)

    async def execute_step(self) -> bool:
        """
        Executes a single step of the agent run.
        Returns:
            bool: True if the run should continue, False if it has stopped (completed, failed, paused, cancelled).
        """
        # 1. Fetch current run status
        run = await agent_state.get_agent_run(self.db, self.run_id)
        if not run:
            logger.error(f"Agent run not found: {self.run_id}")
            return False

        if run.status in ("completed", "failed", "cancelled", "paused", "waiting_approval"):
            logger.info(f"Agent run {self.run_id} is in terminal, paused, or waiting approval state: {run.status}")
            return False

        # Ensure status is 'running' if it was queued
        if run.status == "queued":
            run = await agent_state.update_run(self.db, self.run_id, status="running")
            self.obs.record_run_started(run.agent_id, run.tenant_id)

        # 2. Retrieve agent definition
        agent_def = await agent_state.get_agent_definition(self.db, run.agent_id)
        if not agent_def:
            await agent_state.update_run(
                self.db, self.run_id, status="failed", failure_reason="Agent definition not found", completed_at=utc_now()
            )
            return False

        # 3. Check execution limits
        # Max steps check
        if run.total_steps >= agent_def.max_steps:
            logger.warning(f"Run {self.run_id} exceeded max steps: {agent_def.max_steps}")
            await agent_state.update_run(
                self.db, self.run_id, status="failed", failure_reason="Max steps exceeded", completed_at=utc_now()
            )
            await agent_state.log_run_event(self.db, self.run_id, "limit_exceeded", {"reason": "max_steps"})
            return False

        # Max runtime check
        started_at = run.started_at
        if started_at and started_at.tzinfo is None:
            from datetime import timezone
            started_at = started_at.replace(tzinfo=timezone.utc)
        elapsed = (utc_now() - started_at).total_seconds()
        if elapsed > agent_def.max_runtime_seconds:
            logger.warning(f"Run {self.run_id} exceeded max runtime: {elapsed}s > {agent_def.max_runtime_seconds}s")
            await agent_state.update_run(
                self.db, self.run_id, status="failed", failure_reason="Max runtime seconds exceeded", completed_at=utc_now()
            )
            await agent_state.log_run_event(self.db, self.run_id, "limit_exceeded", {"reason": "max_runtime_seconds"})
            self.obs.record_run_failure(run.agent_id, "max_runtime_exceeded")
            return False

        # Check if we are resuming from an approved approval request
        approved_req = None
        if run.total_steps > 0:
            from sqlalchemy import select
            from app.models.agents import AgentApprovalRequest
            stmt = select(AgentApprovalRequest).where(
                AgentApprovalRequest.agent_run_id == self.run_id,
                AgentApprovalRequest.status == "approved"
            )
            res = await self.db.execute(stmt)
            reqs = res.scalars().all()
            for r in reqs:
                ctx = r.sanitized_context or {}
                if ctx.get("step_number") == run.total_steps:
                    approved_req = r
                    break

        if approved_req:
            logger.info(f"Resuming run {self.run_id} from approved request {approved_req.id}")
            tool_name = approved_req.sanitized_context.get("tool_name")
            tool_input = approved_req.raw_tool_input
            step_number = run.total_steps
        else:
            # 4. Determine next action via LLM provider
            start_time = time.time()
            
            # We only pass prompt hash to avoid exposing full prompt in logs by default
            prompt_hash = run.input_hash or ""
            instructions_hash = agent_state.compute_sha256(agent_def.instructions)
            allowed_tools = agent_def.allowed_tools or []

            try:
                decision = await self.llm_provider.generate(
                    prompt_hash=prompt_hash,
                    system_instructions_hash=instructions_hash,
                    allowed_tools=allowed_tools
                )
            except Exception as e:
                logger.exception("LLM generation failed")
                latency_ms = int((time.time() - start_time) * 1000)
                await agent_state.log_run_step(
                    db=self.db,
                    run_id=self.run_id,
                    step_number=run.total_steps + 1,
                    step_type="model_call",
                    input_data={"prompt_hash": prompt_hash},
                    output_data={},
                    status="failed",
                    latency_ms=latency_ms,
                    error=str(e)
                )
                await agent_state.update_run(
                    self.db, self.run_id, status="failed", failure_reason=f"LLM generation error: {str(e)}", completed_at=utc_now()
                )
                self.obs.record_step(run.agent_id, "model_call", latency_ms, "failed")
                self.obs.record_run_failure(run.agent_id, "llm_generation_error")
                return False

            latency_ms = int((time.time() - start_time) * 1000)
            step_number = run.total_steps + 1
            self.obs.record_step(run.agent_id, "model_call", latency_ms, "success")

            # Record tokens and update run totals
            usage = decision.get("usage", {})
            if usage:
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                self.obs.record_tokens(run.agent_id, prompt_tokens, completion_tokens)
                
                # Update run stats
                run.total_tokens += (prompt_tokens + completion_tokens)
                # Simple cost estimation (e.g., 0.05 BRL per 1k tokens as a placeholder if not provided)
                cost_est = decision.get("cost_brl") or ((prompt_tokens + completion_tokens) * 0.00005)
                run.estimated_cost_brl += cost_est
                self.obs.record_cost(run.agent_id, cost_est)
                await self.db.commit()

            # 5. Process decision
            decision_type = decision.get("type", "final")

            # Policy evaluation
            policy_decision, reason = await self.policy_engine.evaluate_action(
                agent_def, run, {"task_type": decision_type, **decision}
            )
            
            if policy_decision == PolicyDecision.DENY:
                logger.warning(f"Action denied by policy: {reason}")
                await agent_state.log_run_event(self.db, self.run_id, "policy_denial", {"reason": reason})
                self.obs.record_policy_denial(run.agent_id, decision.get("tool_name", "model_call"))
                await agent_state.update_run(self.db, self.run_id, status="failed", failure_reason=f"Policy denial: {reason}", completed_at=utc_now())
                return False

            if decision_type == "tool_call":
                tool_name = decision.get("tool_name")
                tool_input = decision.get("tool_input", {})

                # Log the model call step
                await agent_state.log_run_step(
                    db=self.db,
                    run_id=self.run_id,
                    step_number=step_number,
                    step_type="model_call",
                    input_data={"prompt_hash": prompt_hash},
                    output_data={"tool_name": tool_name, "tool_input_hash": agent_state.compute_sha256(tool_input)},
                    status="success",
                    latency_ms=latency_ms,
                )

                # Check if human approval is required
                from app.services.agents.human_approval import check_approval_required, create_approval_request
                from app.models.agents import AgentApprovalRequest
                from sqlalchemy import select

                approval_required, risk_level, reason, required_role = await check_approval_required(
                    db=self.db,
                    run_id=self.run_id,
                    tool_name=tool_name,
                    tool_input=tool_input
                )

                if approval_required:
                    # Check for pending approval request
                    stmt_pending = select(AgentApprovalRequest).where(
                        AgentApprovalRequest.agent_run_id == self.run_id,
                        AgentApprovalRequest.status == "pending"
                    )
                    res_pending = await self.db.execute(stmt_pending)
                    pending_reqs = res_pending.scalars().all()
                    pending_request = None
                    for req in pending_reqs:
                        ctx = req.sanitized_context or {}
                        if ctx.get("tool_name") == tool_name and ctx.get("step_number") == step_number:
                            pending_request = req
                            break

                    if not pending_request:
                        # Update run to waiting_approval
                        await agent_state.update_run(self.db, self.run_id, status="waiting_approval")
                        await agent_state.log_run_event(
                            self.db,
                            self.run_id,
                            "waiting_approval",
                            {"tool_name": tool_name, "risk_level": risk_level, "reason": reason}
                        )
                        # Create request
                        await create_approval_request(
                            db=self.db,
                            run_id=self.run_id,
                            tool_name=tool_name,
                            tool_input=tool_input,
                            risk_level=risk_level,
                            reason=reason,
                            required_role=required_role,
                            step_number=step_number,
                        )
                    else:
                        if run.status != "waiting_approval":
                            await agent_state.update_run(self.db, self.run_id, status="waiting_approval")
                    return False

            elif decision_type == "memory_read":
                return await self._handle_memory_read(decision)

            elif decision_type == "memory_write":
                return await self._handle_memory_write(decision)

            elif decision_type == "handoff":
                return await self._handle_handoff(decision)

            else:
                # Final output or final decision step
                final_output = decision.get("output", "")
                
                # Log final step
                await agent_state.log_run_step(
                    db=self.db,
                    run_id=self.run_id,
                    step_number=step_number,
                    step_type="final",
                    input_data={"prompt_hash": prompt_hash},
                    output_data={"output_hash": agent_state.compute_sha256(final_output)},
                    status="success",
                    latency_ms=latency_ms,
                )

                # Complete the run
                await agent_state.update_run(
                    db=self.db,
                    run_id=self.run_id,
                    status="completed",
                    output_hash=agent_state.compute_sha256(final_output),
                    completed_at=utc_now(),
                )
                self.obs.record_run_status(run.agent_id, "completed")
                return False

        # Create checkpoint before tool call
        snapshot_before = {
            "step_number": step_number,
            "status": "before_tool_call",
            "tool_name": tool_name,
            "tool_input_hash": agent_state.compute_sha256(tool_input),
        }
        await agent_state.create_run_checkpoint(self.db, self.run_id, step_number, snapshot_before)

        # Run the tool call
        tool_start_time = time.time()
        tool_error = None
        tool_output = None

        # Check if execution is enabled
        if not self.settings.agent_execution_enabled:
            logger.info(f"AGENT_EXECUTION_ENABLED is false. Mocking tool call: {tool_name}")
            tool_output = {
                "result": f"Simulated output for tool '{tool_name}' (AGENT_EXECUTION_ENABLED=false)"
            }
        else:
            try:
                if self.tool_runner:
                    tool_output = await self.tool_runner(tool_name, tool_input)
                else:
                    # Default runner if none provided
                    tool_output = {"result": f"Mock output for tool {tool_name}"}
            except Exception as ex:
                logger.exception(f"Tool {tool_name} execution failed")
                tool_error = str(ex)
                tool_output = {"error": tool_error}

        tool_latency = int((time.time() - tool_start_time) * 1000)
        tool_step_number = step_number + 1
        
        self.obs.record_step(run.agent_id, "tool_call", tool_latency, "failed" if tool_error else "success")
        self.obs.record_tool_call(run.agent_id, tool_name, tool_latency, success=(tool_error is None), error_type=tool_error)

        # Log tool call step
        await agent_state.log_run_step(
            db=self.db,
            run_id=self.run_id,
            step_number=tool_step_number,
            step_type="tool_call",
            input_data={"tool_name": tool_name, "tool_input_hash": agent_state.compute_sha256(tool_input)},
            output_data=tool_output,
            status="failed" if tool_error else "success",
            latency_ms=tool_latency,
            error=tool_error,
        )
        
        # Log summarized event for observability timeline
        await agent_state.log_run_event(
            self.db,
            self.run_id,
            "tool_output",
            {
                "tool_name": tool_name,
                "status": "failed" if tool_error else "success",
                "summary": self.obs.summarize_tool_output(tool_output)
            }
        )

        # Create checkpoint after tool call
        snapshot_after = {
            "step_number": tool_step_number,
            "status": "after_tool_call",
            "tool_name": tool_name,
            "tool_output_hash": agent_state.compute_sha256(tool_output),
            "success": tool_error is None
        }
        await agent_state.create_run_checkpoint(self.db, self.run_id, tool_step_number, snapshot_after)
        
        # Create receipt for execution audit
        await agent_state.create_run_receipt(
            db=self.db,
            run_id=self.run_id,
            step_number=tool_step_number,
            receipt_data={
                "tool_name": tool_name,
                "tool_input_hash": agent_state.compute_sha256(tool_input),
                "tool_output_hash": agent_state.compute_sha256(tool_output),
                "latency_ms": tool_latency,
                "success": tool_error is None
            },
            signature=f"sig_{uuid.uuid4().hex[:12]}"
        )

        return True

    async def _handle_memory_read(self, decision: dict) -> bool:
        run = await agent_state.get_agent_run(self.db, self.run_id)
        memory_type = decision.get("memory_type", "short_term")
        query = decision.get("query")
        
        start_time = time.time()
        try:
            items = await self.memory.read_memory(
                tenant_id=run.tenant_id,
                agent_id=run.agent_id,
                memory_type=memory_type,
                run_id=self.run_id
            )
            latency_ms = int((time.time() - start_time) * 1000)
            
            await agent_state.log_run_step(
                db=self.db,
                run_id=self.run_id,
                step_number=run.total_steps + 1,
                step_type="memory_read",
                input_data={"memory_type": memory_type, "query": query},
                output_data={"items_count": len(items)},
                status="success",
                latency_ms=latency_ms
            )
            self.obs.record_memory_operation(run.agent_id, "read")
            # In a real scenario, we'd feed items back to the LLM context
            return True
        except Exception as e:
            logger.exception("Memory read failed")
            return False

    async def _handle_memory_write(self, decision: dict) -> bool:
        run = await agent_state.get_agent_run(self.db, self.run_id)
        memory_type = decision.get("memory_type", "short_term")
        content = decision.get("content")
        summary = decision.get("summary")
        
        start_time = time.time()
        try:
            item = await self.memory.write_memory(
                tenant_id=run.tenant_id,
                agent_id=run.agent_id,
                memory_type=memory_type,
                content=content,
                summary=summary,
                run_id=self.run_id
            )
            latency_ms = int((time.time() - start_time) * 1000)
            
            await agent_state.log_run_step(
                db=self.db,
                run_id=self.run_id,
                step_number=run.total_steps + 1,
                step_type="memory_write",
                input_data={"memory_type": memory_type, "summary": summary},
                output_data={"item_id": str(item.id)},
                status="success",
                latency_ms=latency_ms
            )
            self.obs.record_memory_operation(run.agent_id, "write")
            return True
        except Exception as e:
            logger.exception("Memory write failed")
            return False

    async def _handle_handoff(self, decision: dict) -> bool:
        run = await agent_state.get_agent_run(self.db, self.run_id)
        target_agent_id = decision.get("target_agent_id")
        reason = decision.get("reason", "No reason provided")
        context = decision.get("context", {})
        
        start_time = time.time()
        try:
            target_run_id = await self.handoff.initiate_handoff(
                source_run_id=self.run_id,
                target_agent_id=uuid.UUID(str(target_agent_id)),
                reason=reason,
                context=context
            )
            latency_ms = int((time.time() - start_time) * 1000)
            
            await agent_state.log_run_step(
                db=self.db,
                run_id=self.run_id,
                step_number=run.total_steps + 1,
                step_type="handoff",
                input_data={"target_agent_id": str(target_agent_id), "reason": reason},
                output_data={"target_run_id": str(target_run_id)},
                status="success",
                latency_ms=latency_ms
            )
            # Finish current run as it handed off
            await agent_state.update_run(
                self.db, self.run_id, status="completed", failure_reason=f"Handed off to {target_agent_id}"
            )
            return False
        except Exception as e:
            logger.exception("Handoff failed")
            return False
