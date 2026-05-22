import uuid
import time
import logging
import json
from typing import Any, Dict, Optional, List, Callable
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_settings
from app.core.time import utc_now
from app.services.agents import agent_state
from app.services.agents.agent_observability import AgentObservabilityService
from app.services.agents.agent_memory import AgentMemoryService
from app.services.agents.agent_policy_engine import AgentPolicyEngine, PolicyDecision
from app.services.agents.agent_llm_provider import (
    AgentLLMProvider, 
    get_agent_llm_provider, 
    MockAgentLLMProvider as MockLLMProvider
)
from app.services.agents.agent_handoffs import AgentHandoffService
from app.models.agents import AgentPlan
from app.services.agents.agent_planner import AgentPlanner
from app.services.agents.task_engine import TaskEngine

logger = logging.getLogger(__name__)

# Re-export for tests that import from this module
MockLLMProvider = MockLLMProvider


class AgentExecutor:
    def __init__(
        self,
        db: AsyncSession,
        run_id: uuid.UUID,
        llm_provider: Optional[AgentLLMProvider] = None,
        tool_runner: Optional[Callable[[str, Any], Any]] = None,
    ):
        self.db = db
        self.run_id = run_id
        self.settings = get_settings()
        self.tool_runner = tool_runner
        self.obs = AgentObservabilityService(db)
        self.memory = AgentMemoryService(db)
        self.policy_engine = AgentPolicyEngine(db)
        self.handoff = AgentHandoffService(db)
        self.planner = AgentPlanner(db)
        self.task_engine = TaskEngine(db)
        
        # Initialize LLM provider if not provided
        if llm_provider:
            self.llm_provider = llm_provider
        else:
            # We'll need an InferenceProxy if we want the gateway provider.
            # Usually it's better to pass it in or get it from deps.
            # For now, let's try to get it from a global or create a temporary one.
            from app.api.deps import get_inference_proxy
            try:
                proxy = get_inference_proxy()
            except Exception:
                # Fallback or manual init if outside request context
                from app.services.queue_manager import QueueManager
                from app.services.circuit_breaker import CircuitBreaker
                # This is a bit heavy, maybe AgentExecutor should be initialized 
                # with the provider already.
                proxy = None 
            
            self.llm_provider = get_agent_llm_provider(db, proxy)

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
            await self.obs.record_run_start(run.agent_id, run.id, run.tenant_id)

        # 2. Retrieve agent definition
        agent_def = await agent_state.get_agent_definition(self.db, run.agent_id)
        if not agent_def:
            await agent_state.update_run(
                self.db, self.run_id, status="failed", failure_reason="Agent definition not found", completed_at=utc_now()
            )
            await self.obs.record_run_failure(run.agent_id, run.id, "Agent definition not found")
            return False

        # 3. Check execution limits
        # Max steps check
        if run.total_steps >= agent_def.max_steps:
            logger.warning(f"Run {self.run_id} exceeded max steps: {agent_def.max_steps}")
            await agent_state.update_run(
                self.db, self.run_id, status="failed", failure_reason="Max steps exceeded", completed_at=utc_now()
            )
            await agent_state.log_run_event(self.db, self.run_id, "limit_exceeded", {"reason": "max_steps"})
            await self.obs.record_run_failure(run.agent_id, run.id, "Max steps exceeded")
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
            await self.obs.record_run_failure(run.agent_id, run.id, "max_runtime_exceeded")
            return False

        # Max tokens check
        if agent_def.max_tokens is not None and run.total_tokens >= agent_def.max_tokens:
            logger.warning(f"Run {self.run_id} exceeded max tokens: {run.total_tokens} >= {agent_def.max_tokens}")
            await agent_state.update_run(
                self.db, self.run_id, status="failed", failure_reason="Max tokens exceeded", completed_at=utc_now()
            )
            await agent_state.log_run_event(self.db, self.run_id, "limit_exceeded", {"reason": "max_tokens"})
            await self.obs.record_run_failure(run.agent_id, run.id, "max_tokens_exceeded")
            return False

        # Max cost check
        if agent_def.max_cost_brl is not None and run.estimated_cost_brl >= agent_def.max_cost_brl:
            logger.warning(f"Run {self.run_id} exceeded max cost: {run.estimated_cost_brl} >= {agent_def.max_cost_brl}")
            await agent_state.update_run(
                self.db, self.run_id, status="failed", failure_reason="Max cost BRL exceeded", completed_at=utc_now()
            )
            await agent_state.log_run_event(self.db, self.run_id, "limit_exceeded", {"reason": "max_cost_brl"})
            await self.obs.record_run_failure(run.agent_id, run.id, "max_cost_exceeded")
            return False

        # Check if we are resuming from an approved approval request
        approved_req = None
        if run.total_steps > 0:
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
            # Check if there is an active plan for this run
            stmt_plan = select(AgentPlan).where(AgentPlan.agent_run_id == self.run_id, AgentPlan.status == "executing")
            res_plan = await self.db.execute(stmt_plan)
            active_plan = res_plan.scalar_one_or_none()
            
            if active_plan:
                logger.info(f"Continuing execution of plan {active_plan.id} for run {self.run_id}")
                await self.task_engine.execute_plan(active_plan.id)
                # After execute_plan returns, it might have finished or paused for approval
                await self.db.refresh(active_plan)
                if active_plan.status == "completed":
                    await agent_state.update_run(self.db, self.run_id, status="completed", completed_at=utc_now())
                    await self.obs.record_run_completion(run.agent_id, run.id)
                    return False
                return True

            # 4. Determine next action via LLM provider
            start_time = time.time()
            
            # We only pass prompt hash to avoid exposing full prompt in logs by default
            prompt_hash = run.input_hash or ""
            instructions_hash = agent_state.compute_sha256(agent_def.instructions)
            allowed_tools = agent_def.allowed_tools or []

            # -- Memory Context Injection --
            memory_context_data = {}
            if self.settings.agent_memory_context_injection_enabled and self.settings.agent_memory_enabled:
                try:
                    memory_context_data = await self.memory.build_memory_context(
                        tenant_id=run.tenant_id,
                        agent_id=run.agent_id,
                        query=run.input_text or "",
                        user_id=getattr(run, "user_id", None),
                        max_tokens=1024,
                        top_k=5,
                    )
                    if memory_context_data.get("context_block"):
                        original_instructions = agent_def.instructions
                        agent_def.instructions = (
                            f"{original_instructions}\n\n{memory_context_data['context_block']}"
                        )
                except Exception as e:
                    logger.warning(f"Memory context injection failed: {e}")
                    memory_context_data = {}

            try:
                decision = await self.llm_provider.generate(
                    agent_def=agent_def,
                    run=run,
                    allowed_tools=allowed_tools
                )
            except Exception as e:
                if memory_context_data.get("context_block"):
                    agent_def.instructions = original_instructions
                logger.exception("LLM generation failed")
                latency_ms = int((time.time() - start_time) * 1000)
                await agent_state.log_run_step(
                    db=self.db,
                    run_id=self.run_id,
                    step_number=run.total_steps + 1,
                    step_type="model_call",
                    input_data={"prompt_hash": prompt_hash},
                    output_data={"memory_ids": memory_context_data.get("memory_ids", [])},
                    status="failed",
                    latency_ms=latency_ms,
                    error=str(e)
                )
                await agent_state.update_run(
                    self.db, self.run_id, status="failed", failure_reason=f"LLM generation error: {str(e)}", completed_at=utc_now()
                )
                await self.obs.record_step(run.agent_id, run.id, "model_call", latency_ms)
                await self.obs.record_run_failure(run.agent_id, run.id, "llm_generation_error")
                return False

            if memory_context_data.get("context_block"):
                agent_def.instructions = original_instructions
            latency_ms = int((time.time() - start_time) * 1000)
            step_number = run.total_steps + 1
            await self.obs.record_step(run.agent_id, run.id, "model_call", latency_ms)

            memory_ids = memory_context_data.get("memory_ids", [])
            if memory_ids:
                for mid in memory_ids:
                    try:
                        await self.memory._log_access(
                            run.tenant_id, run.agent_id, uuid.UUID(mid), "read", self.run_id
                        )
                    except Exception:
                        pass

            # Record tokens and update run totals
            usage = decision.get("usage", {})
            if usage:
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                
                # Update run stats
                run.total_tokens += (prompt_tokens + completion_tokens)
                # Simple cost estimation
                cost_est = decision.get("cost_brl") or ((prompt_tokens + completion_tokens) * 0.00005)
                run.estimated_cost_brl += cost_est
                await self.obs.record_cost(run.agent_id, run.id, cost_est, prompt_tokens, completion_tokens)
                await self.db.commit()

            # 5. Process decision
            decision_type = decision.get("type", "final")
            
            # Metadata for logging
            step_metadata = {
                "backend_id": decision.get("backend_id"),
                "backend_name": decision.get("backend_name"),
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
                "cost_brl": decision.get("cost_brl"),
                "memory_ids": memory_context_data.get("memory_ids", []),
            }

            # Policy evaluation
            policy_decision, reason = await self.policy_engine.evaluate_action(
                agent_def, run, {"task_type": decision_type, **decision}
            )
            
            if policy_decision == PolicyDecision.DENY:
                logger.warning(f"Action denied by policy: {reason}")
                await agent_state.log_run_event(self.db, self.run_id, "policy_denial", {"reason": reason})
                await self.obs.record_policy_denial(run.agent_id, run.id, decision.get("tool_name", "model_call"))
                await agent_state.update_run(self.db, self.run_id, status="failed", failure_reason=f"Policy denial: {reason}", completed_at=utc_now())
                await self.obs.record_run_failure(run.agent_id, run.id, "policy_denial")
                return False

            if decision_type == "tool_call":
                tool_name = decision.get("tool_name")
                tool_input = decision.get("tool_input", {})
                await agent_state.log_run_step(
                    db=self.db,
                    run_id=self.run_id,
                    step_number=step_number,
                    step_type="model_call",
                    input_data={"prompt_hash": prompt_hash},
                    output_data={"decision": "tool_call", "tool_name": tool_name},
                    status="success",
                    latency_ms=latency_ms,
                    metadata=step_metadata,
                )

                # Check if human approval is required
                from app.services.agents.human_approval import check_approval_required, create_approval_request
                from app.models.agents import AgentApprovalRequest

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
            
            elif decision_type == "planning":
                goal = decision.get("goal", run.input_text)
                tasks = decision.get("tasks", [])
                plan = await self.planner.create_plan(self.run_id, goal, tasks)
                
                await agent_state.log_run_step(
                    db=self.db,
                    run_id=self.run_id,
                    step_number=step_number,
                    step_type="planning",
                    input_data={"goal": goal},
                    output_data={"plan_id": str(plan.id), "tasks_count": len(tasks)},
                    status="success",
                    latency_ms=latency_ms,
                    metadata=step_metadata,
                )
                
                if plan.requires_approval and self.settings.agent_human_approval_enabled:
                    plan.status = "draft"
                    await agent_state.update_run(self.db, self.run_id, status="waiting_approval")
                    # logic to create approval request for the plan
                else:
                    plan.status = "executing"
                    await self.db.commit()
                    await self.task_engine.execute_plan(plan.id)
                
                return True

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
                    metadata=step_metadata,
                )
                
                # Store assistant final response in memory
                if self.settings.agent_memory_enabled:
                    await self.memory.write_memory(
                        tenant_id=run.tenant_id,
                        agent_id=run.agent_id,
                        memory_type="short_term",
                        content=final_output,
                        summary="Assistant: Final Response",
                        run_id=self.run_id
                    )

                # Complete the run
                await agent_state.update_run(
                    db=self.db,
                    run_id=self.run_id,
                    status="completed",
                    output_hash=agent_state.compute_sha256(final_output),
                    completed_at=utc_now(),
                )
                await agent_state.log_run_event(
                    self.db,
                    self.run_id,
                    "run_completed",
                    {"completed_at": str(utc_now())}
                )
                await self.obs.record_run_completion(run.agent_id, run.id)
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
                from app.models.agents import AgentTool, AgentRegistryEntry
                from app.services.agents.tool_executor import execute_tool

                stmt = select(AgentTool).where(
                    AgentTool.name == tool_name,
                    AgentTool.enabled == True
                )
                res = await self.db.execute(stmt)
                agent_tool = res.scalar_one_or_none()

                if agent_tool:
                    agent_entry_stmt = select(AgentRegistryEntry).where(AgentRegistryEntry.agent_id == run.agent_id)
                    agent_entry_res = await self.db.execute(agent_entry_stmt)
                    agent_entry = agent_entry_res.scalar_one_or_none()

                    tool_callable = None
                    if self.tool_runner:
                        async def runner_wrapper(**kwargs):
                            return await self.tool_runner(tool_name, kwargs)
                        tool_callable = runner_wrapper

                    tool_output = await execute_tool(
                        db=self.db,
                        tool=agent_tool,
                        parameters=tool_input,
                        run_id=self.run_id,
                        agent=agent_entry,
                        tenant_id=run.tenant_id,
                        is_dry_run=False,
                        tool_callable=tool_callable
                    )
                else:
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
        
        await self.obs.record_step(run.agent_id, run.id, "tool_call", tool_latency)
        await self.obs.record_tool_call(run.agent_id, run.id, tool_name, tool_latency, success=(tool_error is None))

        # Store tool output in memory for history
        if self.settings.agent_memory_enabled:
            await self.memory.write_memory(
                tenant_id=run.tenant_id,
                agent_id=run.agent_id,
                memory_type="short_term",
                content=json.dumps(tool_output),
                summary="Tool: Output",
                run_id=self.run_id
            )

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
                "summary": str(tool_output)[:200]
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
            await self.obs.record_memory_op(run.agent_id, run.id, "read", latency_ms)
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
            await self.obs.record_memory_op(run.agent_id, run.id, "write", latency_ms)
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
            await self.obs.record_handoff(run.agent_id, uuid.UUID(str(target_agent_id)), run.id)
            # Finish current run as it handed off
            await agent_state.update_run(
                self.db, self.run_id, status="completed", failure_reason=f"Handed off to {target_agent_id}"
            )
            await self.obs.record_run_completion(run.agent_id, run.id)
            return False
        except Exception as e:
            logger.exception("Handoff failed")
            return False
