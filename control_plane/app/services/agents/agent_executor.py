# Owner: agent-platform
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
from app.services.agents.agent_budget import AgentBudgetService
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
from app.services.agents.agent_receipts import AgentReceiptsService
from app.services.agents.reasoning.reasoning_loop import ReasoningLoop

logger = logging.getLogger(__name__)

# Re-export for tests
MockLLMProvider = MockLLMProvider

class AgentExecutor:
    def __init__(
        self,
        db: AsyncSession,
        run_id: uuid.UUID,
        llm_provider: Optional[AgentLLMProvider] = None,
        tool_runner: Optional[Callable[[str, Any], Any]] = None,
        is_replay: bool = False,
    ):
        self.db = db
        self.run_id = run_id
        self.settings = get_settings()
        self.tool_runner = tool_runner
        self.is_replay = is_replay
        self.obs = AgentObservabilityService(db)
        self.receipts = AgentReceiptsService(db)
        self.memory = AgentMemoryService(db)
        self.policy_engine = AgentPolicyEngine(db)
        self.handoff = AgentHandoffService(db)
        self.planner = AgentPlanner(db)
        self.task_engine = TaskEngine(db)
        self.budget_svc = AgentBudgetService()
        
        if llm_provider:
            self.llm_provider = llm_provider
        else:
            from app.api.deps import get_inference_proxy
            try:
                proxy = get_inference_proxy()
            except Exception:
                proxy = None 
            self.llm_provider = get_agent_llm_provider(db, proxy)
        
        self.reasoning_loop = ReasoningLoop(self.llm_provider)

    async def execute_step(self) -> bool:
        run = await agent_state.get_agent_run(self.db, self.run_id)
        if not run or run.status in ("completed", "failed", "cancelled", "paused", "waiting_approval"):
            return False

        if run.status == "queued":
            run = await agent_state.update_run(self.db, self.run_id, status="running")
            await self.obs.record_run_start(run.agent_id, run.id, run.tenant_id)
            await self.db.commit()

        agent_def = await agent_state.get_agent_definition(self.db, run.agent_id)
        if not agent_def:
            await self._fail_run("Agent definition not found")
            await self.db.commit()
            return False

        if await self._check_limits(run, agent_def):
            await self.db.commit()
            return False

        # Class-based budget enforcement
        is_within_budget, reason = await self.budget_svc.validate_run_budget(agent_def, run)
        if not is_within_budget:
            await self._fail_run(f"Budget exceeded: {reason}")
            await self.db.commit()
            return False

        step_number = run.total_steps + 1
        await self.obs.record_step_start(run.id, step_number, "orchestration")

        # 3.1 Planner Execution Policy Check
        from app.services.agents.agent_policy_engine import PolicyRequest
        planner_policy_req = PolicyRequest(
            action_type="planner_exec",
            subject="agent_planner",
            tenant_id=run.tenant_id,
            agent_id=run.agent_id,
            run_id=run.id,
            context={"step_number": step_number}
        )
        planner_decision = await self.policy_engine.evaluate_action_v2(planner_policy_req)
        if planner_decision.result == "deny":
            await self._fail_run(f"Planner execution denied: {planner_decision.reason}")
            await self.db.commit()
            return False

        approved_req = await self._get_approved_request(run)
        if approved_req:
            res = await self._execute_tool_and_process(run, approved_req.sanitized_context.get("tool_name"), approved_req.raw_tool_input, step_number)
            await self.db.commit()
            return res

        active_plan = await self._get_active_plan()
        if active_plan:
            res = await self._continue_plan_execution(run, active_plan)
            await self.db.commit()
            return res

        decision = await self._get_llm_decision(run, agent_def, step_number)
        if decision is None:
            await self.db.commit()
            return False

        decision_type = decision.get("type", "final")
        policy_decision, reason = await self.policy_engine.evaluate_action(agent_def, run, {"task_type": decision_type, **decision})
        await self.obs.record_policy_decision(run.id, policy_decision.value, reason)
        
        if policy_decision == PolicyDecision.DENY:
            await self._fail_run(f"Policy denial: {reason}")
            await self.db.commit()
            return False

        res = False
        if decision_type == "tool_call":
            res = await self._handle_tool_call_decision(run, decision, step_number)
        elif decision_type == "planning":
            res = await self._handle_planning_decision(run, decision, step_number)
        elif decision_type == "memory_read":
            res = await self._handle_memory_op(run, decision, step_number, "read")
        elif decision_type == "memory_write":
            res = await self._handle_memory_op(run, decision, step_number, "write")
        elif decision_type == "handoff":
            res = await self._handle_handoff(run, decision, step_number)
        else:
            res = await self._handle_final_decision(run, decision, step_number)
        
        await self.db.commit()
        return res

    async def _fail_run(self, reason: str):
        await agent_state.update_run(self.db, self.run_id, status="failed", failure_reason=reason, completed_at=utc_now())
        run = await agent_state.get_agent_run(self.db, self.run_id)
        await self.obs.record_run_failure(run.agent_id, run.id, reason)

    async def _check_limits(self, run, agent_def) -> bool:
        if run.total_steps >= agent_def.max_steps:
            await self._fail_run("Max steps exceeded")
            return True
        started_at = run.started_at.replace(tzinfo=None) if run.started_at.tzinfo else run.started_at
        if (utc_now().replace(tzinfo=None) - started_at).total_seconds() > agent_def.max_runtime_seconds:
            await self._fail_run("Max runtime exceeded")
            return True
        return False

    async def _get_approved_request(self, run):
        from app.models.agents import AgentApprovalRequest
        stmt = select(AgentApprovalRequest).where(AgentApprovalRequest.agent_run_id == self.run_id, AgentApprovalRequest.status == "approved")
        res = await self.db.execute(stmt)
        for r in res.scalars().all():
            if (r.sanitized_context or {}).get("step_number") == run.total_steps: return r
        return None

    async def _get_active_plan(self):
        stmt = select(AgentPlan).where(AgentPlan.agent_run_id == self.run_id, AgentPlan.status == "executing")
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def _continue_plan_execution(self, run, plan):
        if self.is_replay: return False
        await self.task_engine.execute_plan(plan.id)
        await self.db.refresh(plan)
        if plan.status == "completed":
            await agent_state.update_run(self.db, self.run_id, status="completed", completed_at=utc_now())
            await self.obs.record_run_completion(run.agent_id, run.id)
            return False
        return True

    async def _get_llm_decision(self, run, agent_def, step_number: int) -> Optional[Dict]:
        start_time = time.time()
        
        # Context Compression
        if self.settings.agent_context_compression_enabled:
            from app.services.agents.reasoning.context_compressor import ContextCompressor
            compressor = ContextCompressor()
            # This requires access to the full history, which might be in memory or db
            # For this prototype, we simulate compression on instructions
            agent_def.instructions = compressor.redact_secrets(agent_def.instructions)

        if self.settings.agent_memory_enabled:
            mem = await self.memory.build_memory_context(tenant_id=run.tenant_id, agent_id=run.agent_id, query=run.input_text or "")
            if mem.get("context_block"): 
                agent_def.instructions += f"\n\n{mem['context_block']}"
                await self.obs.record_memory_op_detailed(self.run_id, "read", "short_term", True)
        
        try:
            decision = await self.reasoning_loop.execute(agent_def=agent_def, run=run, allowed_tools=agent_def.allowed_tools or [])
            latency_ms = int((time.time() - start_time) * 1000)
            await self.obs.record_model_call(self.run_id, "completed", latency_ms, decision.get("usage"))
            await self._update_usage(run, decision)
            return decision
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            await self.obs.record_model_call(self.run_id, "failed", latency_ms, error=str(e))
            await agent_state.log_run_step(self.db, self.run_id, step_number, "model_call", {"input_hash": run.input_hash}, {}, "failed", latency_ms, error=str(e))
            await self._fail_run(f"LLM failure: {str(e)}")
            return None

    async def _update_usage(self, run, decision):
        usage = decision.get("usage", {})
        p_tok, c_tok = usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)
        run.total_tokens += (p_tok + c_tok)
        cost = decision.get("cost_brl") or ((p_tok + c_tok) * 0.00005)
        run.estimated_cost_brl += cost
        await self.obs.record_cost(run.agent_id, run.id, cost, p_tok, c_tok)
        await self.db.commit()

    async def _handle_tool_call_decision(self, run, decision, step_number):
        tool_name, tool_input = decision.get("tool_name"), decision.get("tool_input", {})
        i_hash = agent_state.compute_sha256(tool_input)
        await agent_state.log_run_step(self.db, self.run_id, step_number, "model_call", {"input_hash": run.input_hash}, {"tool_name": tool_name, "tool_input_hash": i_hash})
        
        from app.services.agents.human_approval import check_approval_required, create_approval_request
        req, risk, reason, role = await check_approval_required(self.db, self.run_id, tool_name, tool_input)
        if req:
            await self.obs.record_approval_request(self.run_id, tool_name, reason)
            await agent_state.update_run(self.db, self.run_id, status="waiting_approval")
            await create_approval_request(self.db, self.run_id, tool_name, tool_input, risk, reason, role, step_number)
            return False
        return await self._execute_tool_and_process(run, tool_name, tool_input, step_number + 1)

    async def _execute_tool_and_process(self, run, tool_name, tool_input, step_number):
        if self.is_replay: return False
        await self.obs.record_tool_call_start(self.run_id, tool_name)
        start_time = time.time()
        try:
            from app.models.agents import AgentTool
            from app.services.agents.tool_executor import execute_tool
            stmt = select(AgentTool).where(AgentTool.name == tool_name, AgentTool.enabled == True)
            res = await self.db.execute(stmt)
            tool = res.scalar_one_or_none()
            if not tool: raise ValueError(f"Tool {tool_name} not found")
            
            tool_callable = None
            if self.tool_runner:
                async def runner_wrapper(**kwargs):
                    return await self.tool_runner(tool_name, kwargs)
                tool_callable = runner_wrapper

            output = await execute_tool(
                self.db, tool, tool_input, self.run_id, 
                agent_id=run.agent_id,
                tenant_id=run.tenant_id, 
                is_dry_run=not self.settings.agent_execution_enabled,
                tool_callable=tool_callable
            )
            error = None
        except Exception as e:
            output, error = {"error": str(e)}, str(e)
        
        latency = int((time.time() - start_time) * 1000)
        await self.obs.record_tool_call_result(self.run_id, tool_name, "failed" if error else "completed", latency, error)
        i_hash, o_hash = agent_state.compute_sha256(tool_input), agent_state.compute_sha256(output)
        await self.receipts.create_receipt(self.run_id, step_number, "tool_execution", i_hash, o_hash, success=not error, failure_reason=error)
        await agent_state.log_run_step(self.db, self.run_id, step_number, "tool_call", {"tool_name": tool_name, "input_hash": i_hash}, {"output_hash": o_hash, "result": output}, "success" if not error else "failed", latency, error)
        return True

    async def _handle_planning_decision(self, run, decision, step_number):
        goal, tasks = decision.get("goal", run.input_text), decision.get("tasks", [])
        await self.obs.record_replan(self.run_id, "Replan requested by LLM")
        plan = await self.planner.create_plan(self.run_id, goal, tasks)
        await self.obs.record_plan_depth(run.agent_id, self.run_id, len(tasks))
        await agent_state.log_run_step(self.db, self.run_id, step_number, "planning", {"goal": goal}, {"plan_id": str(plan.id)}, "success")
        if plan.requires_approval and self.settings.agent_human_approval_enabled:
            await agent_state.update_run(self.db, self.run_id, status="waiting_approval")
            return False
        plan.status = "executing"
        await self.db.commit()
        if not self.is_replay: await self.task_engine.execute_plan(plan.id)
        return True

    async def _handle_memory_op(self, run, decision, step_number, op):
        if self.is_replay: return True
        await self.obs.record_memory_op_detailed(self.run_id, op, decision.get("memory_type", "short_term"), True)
        # Log step logic omitted for brevity
        return True

    async def _handle_handoff(self, run, decision, step_number):
        if self.is_replay: return False
        target = decision.get("target_agent_id")
        await self.handoff.initiate_handoff(self.run_id, uuid.UUID(str(target)), decision.get("reason", ""), decision.get("context", {}))
        await self.obs.record_handoff(run.agent_id, uuid.UUID(str(target)), run.id)
        await agent_state.update_run(self.db, self.run_id, status="completed", failure_reason=f"Handed off to {target}")
        await self.obs.record_run_completion(run.agent_id, run.id)
        return False

    async def _handle_final_decision(self, run, decision, step_number):
        output = decision.get("output", "")
        o_hash = agent_state.compute_sha256(output)
        await agent_state.log_run_step(self.db, self.run_id, step_number, "final", {"input_hash": run.input_hash}, {"output_hash": o_hash}, "success")
        if self.settings.agent_memory_enabled and not self.is_replay:
            await self.memory.write_memory(
                tenant_id=run.tenant_id, agent_id=run.agent_id, 
                memory_type="short_term", content=output, 
                summary="Final Response", run_id=self.run_id
            )
        await agent_state.update_run(self.db, self.run_id, status="completed", output_hash=o_hash, completed_at=utc_now())
        await self.obs.record_run_completion(run.agent_id, run.id)
        return False
