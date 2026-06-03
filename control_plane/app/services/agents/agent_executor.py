# Owner: agent-platform
import uuid
import time
import logging
import json
from typing import Any, Dict, Optional, List, Callable, Tuple
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
    MockAgentLLMProvider as MockLLMProvider,
    ProviderResponse,
    MockProviderError,
    ProviderUnavailableError,
)
from app.services.agents.agent_handoffs import AgentHandoffService
from app.models.agents import AgentPlan
from app.services.agents.agent_planner import AgentPlanner
from app.services.agents.planning.step_cache import StepCache
from app.services.agents.task_engine import TaskEngine
from app.services.agents.agent_receipts import AgentReceiptsService
from app.services.agents.reasoning.reasoning_loop import ReasoningLoop

logger = logging.getLogger(__name__)


class ExecutorSimulationError(RuntimeError):
    pass

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
        self.step_cache = StepCache(db)
        
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
        self.deployment_mode = getattr(self.settings, "deployment_mode", "appliance")
        
        from app.services.agents.guardrails.guardrail_policy import GuardrailPolicyOrchestrator
        self.guardrails = GuardrailPolicyOrchestrator(db)

    async def _check_input_guardrails(self, run) -> bool:
        """Checks input guardrails and returns True if blocked."""
        prompt = getattr(run, "input_text", "") or ""
        if not prompt: return False

        decision, reason = await self.guardrails.check_input(run.id, run.tenant_id, prompt)
        if decision == "block":
            await self._fail_run(f"Input blocked by safety guardrails: {reason}")
            return True
        return False

    async def _check_output_guardrails(self, run, content: str) -> Tuple[bool, str]:
        """Checks output guardrails. Returns (is_blocked, sanitized_content)."""
        decision, reason, sanitized = await self.guardrails.check_output(run.id, run.tenant_id, content)
        if decision == "block":
            await self._fail_run(f"Output blocked by safety guardrails: {reason}")
            return True, content
        
        if decision == "require_human_review":
            # Pause run and wait for HITL
            await agent_state.update_run(self.db, self.run_id, status="waiting_approval")
            # In a real system, we'd create a specific GuardrailApprovalRequest
            return True, sanitized

        return False, sanitized

    async def execute_step(self) -> bool:
        # PII Protection and OTel Tracing Integration
        from app.services.security.pii_gateway import pii_gateway
        from app.services.agents.telemetry.native_otel import agent_tracer
        
        run = await agent_state.get_agent_run(self.db, self.run_id)
        if not run or run.status in ("completed", "failed", "cancelled", "paused", "waiting_approval"):
            return False

        # Sanitize input text if present
        if run.input_text:
            run.input_text = pii_gateway.redact_text(run.input_text)

        agent_def = await agent_state.get_agent_definition(self.db, run.agent_id)
        if not agent_def:
            await self._fail_run("Agent definition not found")
            await self.db.commit()
            return False

        with agent_tracer.start_agent_span(agent_def.name, str(run.id)) as span:
            logger.info(f"Executing step for agent {agent_def.name} under PII Gateway protection")
            
            # --- Debugger Integration ---
        if self.settings.agent_debugger_enabled:
            from app.services.agents.debugger.live_stepper import LiveStepper
            from app.services.agents.debugger.debug_sessions import DebugSessionManager
            from app.services.agents.debugger.breakpoints import BreakpointManager
            stepper = LiveStepper(
                self.db, 
                DebugSessionManager(self.db), 
                BreakpointManager(self.db)
            )
            await stepper.check_and_pause(
                run.id, run.tenant_id, run.total_steps + 1, 
                "step_start", {"run_status": run.status, "total_steps": run.total_steps}
            )
            # Re-fetch run in case status changed during pause
            run = await agent_state.get_agent_run(self.db, self.run_id)
        # ----------------------------

        if run.status == "queued":
            run = await agent_state.update_run(self.db, self.run_id, status="running")
            await self.obs.record_run_start(run.agent_id, run.id, run.tenant_id)
            await self.db.commit()

        # --- Guardrail Check ---
        if await self._check_input_guardrails(run):
            return False
        # ----------------------

        agent_def = await agent_state.get_agent_definition(self.db, run.agent_id)

        if agent_def:
            agent_def = await self._apply_candidate_overrides_if_evaluating(run, agent_def)
        else:
            await self._fail_run("Agent definition not found")
            await self.db.commit()
            return False

        if self.settings.prompt_templates_enabled and agent_def.prompt_template_id:
            agent_def = await self._resolve_prompt_template(agent_def, run)

        if await self._check_limits(run, agent_def):
            await self.db.commit()
            return False

        # Class-based budget enforcement
        is_within_budget, reason = await self.budget_svc.validate_run_budget(agent_def, run)
        if not is_within_budget:
            await self._fail_run(f"Budget exceeded: {reason}")
            await self.db.commit()
            return False

        # --- Hard Cost Cap Enforcement ---
        from app.services.agents.budgets.hard_cost_cap import HardCostCapService
        is_within_hard_cap = await HardCostCapService.check_cost_cap(self.db, agent_def, run)
        if not is_within_hard_cap:
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

        # --- Output Guardrail Check ---
        # We check the raw response text if available, or convert the decision to string
        content_to_check = str(decision.get("raw_response", "")) or str(decision)
        is_blocked, sanitized = await self._check_output_guardrails(run, content_to_check)
        if is_blocked:
            return False
        
        # If redacted, we might need to update the decision (simplified for now)
        # ------------------------------

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
        # --- Hard Cost Cap check before LLM call ---
        from app.services.agents.budgets.hard_cost_cap import HardCostCapService
        if not await HardCostCapService.check_cost_cap(self.db, agent_def, run):
            return None

        start_time = time.time()
        
        # Context Compression
        if self.settings.agent_context_compression_enabled:
            from app.services.agents.reasoning.context_compressor import ContextCompressor
            compressor = ContextCompressor()
            agent_def.instructions = compressor.redact_secrets(agent_def.instructions)

        if self.settings.agent_memory_enabled:
            mem = await self.memory.build_memory_context(tenant_id=run.tenant_id, agent_id=run.agent_id, query=run.input_text or "")
            if mem.get("context_block"):
                agent_def.instructions += f"\n\n{mem['context_block']}"
                await self.obs.record_memory_op_detailed(self.run_id, "read", "short_term", True)

        # Session Context Integration
        if run.session_id:
            from app.services.agents.sessions.session_context_builder import SessionContextBuilder
            context_builder = SessionContextBuilder(self.db)
            session_context = await context_builder.build_context_for_llm(
                session_id=run.session_id,
                max_messages=50,
                include_summary=True
            )
            if session_context:
                # We inject the session history into the reasoning loop's input
                # The ReasoningLoop service usually takes the run and agent_def
                # We might need to pass the history explicitly if it's not already handled
                # For now, we'll append it to the instructions or handle it in reasoning_loop
                history_str = "\n".join([f"{m['role']}: {m['content']}" for m in session_context])
                agent_def.instructions += f"\n\nConversation History:\n{history_str}"
                logger.info(f"Injected {len(session_context)} messages from session {run.session_id} into context")

        # Check Cache
        cached_decision = await self.step_cache.get_cached_step(
            agent_id=run.agent_id,
            tenant_id=run.tenant_id,
            step_type="model_call",
            input_data={"instructions": agent_def.instructions, "input_text": run.input_text, "steps": run.total_steps},
            model_version=agent_def.model_id
        )
        if cached_decision:
            logger.info(f"Using cached decision for run {run.id} step {step_number}")
            return cached_decision

        try:
            self._assert_llm_provider_mode_allowed()
            decision = await self.reasoning_loop.execute(agent_def=agent_def, run=run, allowed_tools=agent_def.allowed_tools or [])
            latency_ms = int((time.time() - start_time) * 1000)
            await self.obs.record_model_call(self.run_id, "completed", latency_ms, decision.get("usage"))

            if isinstance(decision, ProviderResponse):
                await self._record_provider_metadata(run, decision)

            await self._update_usage(run, decision)

            # Set Cache
            await self.step_cache.set_cached_step(
                agent_id=run.agent_id,
                tenant_id=run.tenant_id,
                step_type="model_call",
                input_data={"instructions": agent_def.instructions, "input_text": run.input_text, "steps": run.total_steps},
                output_data=decision,
                model_version=agent_def.model_id
            )

            return decision

        except MockProviderError as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Mock provider blocked in production: {e}")
            await self.obs.record_model_call(self.run_id, "failed", latency_ms, error=str(e))
            await agent_state.log_run_step(self.db, self.run_id, step_number, "model_call", {"input_hash": run.input_hash}, {}, "failed", latency_ms, error=str(e))
            await self._fail_run(f"LLM provider denied: {str(e)}")
            return None
        except ProviderUnavailableError as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Provider unavailable: {e}")
            await self.obs.record_model_call(self.run_id, "failed", latency_ms, error=str(e))
            await agent_state.log_run_step(self.db, self.run_id, step_number, "model_call", {"input_hash": run.input_hash}, {}, "failed", latency_ms, error=str(e))
            await self._fail_run(f"Provider unavailable: {str(e)}")
            return None
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.exception(
                "Unhandled LLM decision failure for run %s agent %s step %s",
                self.run_id,
                run.agent_id,
                step_number,
            )
            await self.obs.record_model_call(self.run_id, "failed", latency_ms, error=str(e))
            await agent_state.log_run_step(self.db, self.run_id, step_number, "model_call", {"input_hash": run.input_hash}, {}, "failed", latency_ms, error=str(e))
            await self._fail_run(f"LLM failure: {str(e)}")
            return None

    def _assert_llm_provider_mode_allowed(self) -> None:
        provider_type = getattr(self.llm_provider, "provider_type", None)
        provider_value = getattr(provider_type, "value", provider_type)
        if provider_value != "mock":
            return
        if self.settings.agent_executor_mock_mode:
            return
        if self.deployment_mode in ("pilot", "production", "enterprise_managed"):
            raise MockProviderError(
                f"Mock LLM provider blocked by AgentExecutor in deployment mode '{self.deployment_mode}'. "
                "Set AGENT_EXECUTOR_MOCK_MODE=true for explicit test-only override."
            )
        raise MockProviderError(
            "Mock LLM provider blocked by AgentExecutor. Set AGENT_EXECUTOR_MOCK_MODE=true for explicit test-only use."
        )

    async def _update_usage(self, run, decision):
        if isinstance(decision, ProviderResponse):
            usage = decision.usage
            p_tok = usage.get("prompt_tokens", 0)
            c_tok = usage.get("completion_tokens", 0)
            cost = decision.cost_brl
        else:
            usage = decision.get("usage", {})
            p_tok, c_tok = usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)
            cost = decision.get("cost_brl") or ((p_tok + c_tok) * 0.00005)
        run.total_tokens += (p_tok + c_tok)
        run.estimated_cost_brl += cost
        await self.obs.record_cost(run.agent_id, run.id, cost, p_tok, c_tok)
        try:
            from app.services.agents.agent_usage_meter import AgentUsageMeter
            meter = AgentUsageMeter(self.db)
            await meter.record_run_usage(
                tenant_id=run.tenant_id,
                agent_id=run.agent_id,
                run_id=run.id,
                tokens_consumed=p_tok + c_tok,
                cost_estimated_brl=cost,
                tier_name=getattr(run, "service_tier", "free"),
            )
        except Exception as exc:
            logger.warning(f"Usage metering failed for run {run.id}: {exc}")
        await self.db.commit()

    async def _record_provider_metadata(self, run, decision: ProviderResponse):
        await self.obs.record_model_call(
            self.run_id,
            "completed",
            decision.latency,
            {
                "provider_type": decision.provider_type,
                "model_id": decision.model_id,
                "backend_id": decision.backend_id,
                "execution_mode": decision.execution_mode,
                "fallback_used": decision.fallback_used,
                "validation_status": decision.validation_status,
            }
        )

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
        # --- Hard Cost Cap check before Tool execution ---
        agent_def = await agent_state.get_agent_definition(self.db, run.agent_id)
        if agent_def:
            from app.services.agents.budgets.hard_cost_cap import HardCostCapService
            if not await HardCostCapService.check_cost_cap(self.db, agent_def, run):
                return False

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

            policy_decision_id = None
            exec_mode = self._resolve_executor_tool_mode()
            if exec_mode == "mock":
                output = self._build_simulated_output(
                    mode="mock",
                    tool_name=tool_name,
                    reason="AGENT_EXECUTOR_MOCK_MODE=true",
                    policy_decision_id=policy_decision_id,
                )
            elif exec_mode == "dry_run":
                output = await execute_tool(
                    self.db, tool, tool_input, self.run_id,
                    agent_id=run.agent_id,
                    tenant_id=run.tenant_id,
                    is_dry_run=True,
                    tool_callable=tool_callable
                )
                if isinstance(output, dict):
                    output.setdefault("execution_mode", "dry_run")
                    output["simulated"] = True
                    output.setdefault("reason", "AGENT_EXECUTOR_DRY_RUN_MODE=true")
                    output["policy_decision_id"] = policy_decision_id
            elif exec_mode == "simulation":
                output = self._build_simulated_output(
                    mode="simulation",
                    tool_name=tool_name,
                    reason="AGENT_EXECUTOR_ALLOW_SIMULATION=true and real execution disabled",
                    policy_decision_id=policy_decision_id,
                )
            else:
                if not self.settings.agent_execution_enabled:
                    raise ExecutorSimulationError(
                        "Agent execution is disabled. Enable AGENT_EXECUTION_ENABLED=true or AGENT_EXECUTOR_ALLOW_SIMULATION=true."
                    )
                output = await execute_tool(
                    self.db, tool, tool_input, self.run_id,
                    agent_id=run.agent_id,
                    tenant_id=run.tenant_id,
                    is_dry_run=False,
                    tool_callable=tool_callable
                )
                if isinstance(output, dict):
                    output.setdefault("execution_mode", "real")
                    output.setdefault("simulated", False)
                    output["policy_decision_id"] = policy_decision_id
            error = None
        except Exception as e:
            output, error = {"error": str(e)}, str(e)
        
        # --- Tool Output Guardrail Check ---
        if not error:
            is_blocked, sanitized_output = await self._check_output_guardrails(run, str(output))
            if is_blocked:
                # If blocked, we treat it as an error for the agent loop
                output, error = {"error": "Tool output blocked by safety guardrails"}, "Guardrail violation"
            else:
                # If redacted, we'd ideally update the 'output' dict
                pass
        # -----------------------------------

        latency = int((time.time() - start_time) * 1000)
        await self.obs.record_tool_call_result(self.run_id, tool_name, "failed" if error else "completed", latency, error)
        i_hash, o_hash = agent_state.compute_sha256(tool_input), agent_state.compute_sha256(output)
        await self.receipts.create_receipt(self.run_id, step_number, "tool_execution", i_hash, o_hash, success=not error, failure_reason=error)
        
        step_meta = None
        if tool_name == "web_search" and not error and isinstance(output, dict):
            step_meta = {
                "query_hash": output.get("query_hash"),
                "result_ids": output.get("result_ids"),
                "citation": output.get("citation"),
                "audit_event_id": output.get("audit_event_id"),
            }

        await agent_state.log_run_step(
            self.db,
            self.run_id,
            step_number,
            "tool_call",
            {"tool_name": tool_name, "input_hash": i_hash},
            {"output_hash": o_hash, "result": output},
            "success" if not error else "failed",
            latency_ms=latency,
            metadata=step_meta,
            error=error,
        )
        if error:
            await self._fail_run(f"Tool execution failed: {error}")
            return False
        return True

    def _resolve_executor_tool_mode(self) -> str:
        mock_enabled = bool(getattr(self.settings, "agent_executor_mock_mode", False))
        dry_run_enabled = bool(getattr(self.settings, "agent_executor_dry_run_mode", False))
        simulation_enabled = bool(getattr(self.settings, "agent_executor_allow_simulation", False))

        if mock_enabled:
            return "mock"
        if dry_run_enabled:
            return "dry_run"
        if not self.settings.agent_execution_enabled:
            if simulation_enabled:
                return "simulation"
            return "real"
        return "real"

    def _build_simulated_output(self, *, mode: str, tool_name: str, reason: str, policy_decision_id: Optional[str]) -> Dict[str, Any]:
        return {
            "status": mode,
            "message": f"Simulated execution for tool {tool_name}",
            "execution_mode": mode,
            "simulated": True,
            "reason": reason,
            "policy_decision_id": policy_decision_id,
        }

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
        await agent_state.log_run_step(self.db, self.run_id, step_number, f"memory_{op}", {"input_hash": run.input_hash}, {"op": op, "memory_type": decision.get("memory_type")})
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

    async def _apply_candidate_overrides_if_evaluating(self, run, agent_def):
        if not run.correlation_id or not run.correlation_id.startswith("eval-"):
            return agent_def

        eval_run_id_str = run.correlation_id.replace("eval-", "")
        try:
            eval_run_id = uuid.UUID(eval_run_id_str)
        except ValueError:
            return agent_def

        from app.models.agents import AgentEvalRun
        res_eval = await self.db.execute(select(AgentEvalRun).where(AgentEvalRun.id == eval_run_id))
        eval_run = res_eval.scalar_one_or_none()
        if not eval_run or not eval_run.metadata_json:
            return agent_def

        candidate_id_str = eval_run.metadata_json.get("candidate_id")
        if not candidate_id_str:
            return agent_def

        try:
            candidate_id = uuid.UUID(candidate_id_str)
        except ValueError:
            return agent_def

        from app.models.agent_optimization import (
            AgentOptimizationCandidate,
            AgentPromptCandidate,
            AgentPolicyCandidate,
            AgentToolSelectionCandidate,
        )
        res_cand = await self.db.execute(select(AgentOptimizationCandidate).where(AgentOptimizationCandidate.id == candidate_id))
        candidate = res_cand.scalar_one_or_none()
        if not candidate:
            return agent_def

        if candidate.candidate_type == "prompt":
            res_prompt = await self.db.execute(select(AgentPromptCandidate).where(AgentPromptCandidate.candidate_id == candidate_id))
            prompt_detail = res_prompt.scalar_one_or_none()
            if prompt_detail:
                # Modifying the in-memory object attributes to prevent database persistence
                agent_def.instructions = prompt_detail.prompt_text

        elif candidate.candidate_type == "tool_selection":
            res_tools = await self.db.execute(select(AgentToolSelectionCandidate).where(AgentToolSelectionCandidate.candidate_id == candidate_id))
            tools_detail = res_tools.scalar_one_or_none()
            if tools_detail:
                agent_def.allowed_tools = tools_detail.allowed_tools

        elif candidate.candidate_type == "policy":
            res_policy = await self.db.execute(select(AgentPolicyCandidate).where(AgentPolicyCandidate.candidate_id == candidate_id))
            policy_detail = res_policy.scalar_one_or_none()
            if policy_detail:
                # Set temporary policy_id to let the policy engine load custom rules
                agent_def.policy_id = f"policy-opt-{candidate_id}"

        return agent_def

    async def _resolve_prompt_template(self, agent_def, run) -> Any:
        try:
            from app.models.prompts import PromptTemplateVersion
            from app.services.prompts.prompt_template_renderer import PromptTemplateRenderer
            from app.services.prompts.prompt_template_registry import PromptTemplateRegistryService

            version_id = agent_def.prompt_template_version_id
            if not version_id:
                from app.models.prompts import PromptTemplate
                tmpl_stmt = select(PromptTemplate).where(
                    PromptTemplate.id == agent_def.prompt_template_id
                )
                tmpl_res = await self.db.execute(tmpl_stmt)
                template = tmpl_res.scalar_one_or_none()
                if template and template.active_version_id:
                    version_id = template.active_version_id

            if not version_id:
                return agent_def

            ver_stmt = select(PromptTemplateVersion).where(
                PromptTemplateVersion.id == version_id
            )
            ver_res = await self.db.execute(ver_stmt)
            version = ver_res.scalar_one_or_none()
            if not version:
                return agent_def

            svc = PromptTemplateRegistryService(self.db)
            declared = await svc.get_declared_variables(
                agent_def.prompt_template_id
            )
            declared_list = [
                {"name": v.name, "type": v.var_type, "required": v.required,
                 "default": v.default, "description": v.description}
                for v in declared
            ]

            variables = {
                "input": run.input_text or "",
                "agent_name": agent_def.name,
                "agent_description": agent_def.description or "",
                "tools": str(agent_def.allowed_tools or []),
                "tenant_id": run.tenant_id,
                "user_id": run.user_id or "",
            }

            renderer = PromptTemplateRenderer()
            rendered, hashes = renderer.resolve_instructions(
                template_str=version.content,
                instructions=agent_def.instructions,
                variables=variables,
                declared_vars=declared_list,
            )

            agent_def.instructions = rendered

            if hashes:
                await svc.record_render_event(
                    template_id=agent_def.prompt_template_id,
                    version_id=version_id,
                    tenant_id=run.tenant_id,
                    variables_hash=hashes["variables_hash"],
                    output_hash=hashes["output_hash"],
                    rendered_content_hash=hashes["rendered_content_hash"],
                    agent_run_id=run.id,
                    agent_id=agent_def.id,
                )

        except Exception as e:
            logger.warning(f"Failed to resolve prompt template: {e}")

        return agent_def
