# Owner: agent-platform
import asyncio
import time
import uuid
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, Optional

from app.contracts.agents.task_execution_contract import (
    ApprovalWaitTaskContractV1,
    FinalResponseTaskContractV1,
    HandoffTaskContractV1,
    MemoryReadTaskContractV1,
    MemoryWriteTaskContractV1,
    ModelReasoningTaskContractV1,
    ToolCallTaskContractV1,
    WorkflowSignalTaskContractV1,
)
from app.contracts.base import ContractValidationError
from app.core.config import get_settings
from app.core.time import utc_now
from app.models.agents import AgentPlan, AgentTask, AgentTaskAttempt, AgentTaskDependency, AgentTool
from app.services.agents import agent_state
from app.services.agents.agent_budget import AgentBudgetService
from app.services.agents.agent_handoffs import AgentHandoffService
from app.services.agents.agent_llm_provider import AgentLLMProvider, get_agent_llm_provider
from app.services.agents.agent_memory import AgentMemoryService
from app.services.agents.agent_receipts import AgentReceiptsService
from app.services.agents.compensation import CompensationService
from app.services.agents.human_approval import check_approval_required, create_approval_request
from app.services.agents.tool_adapter_registry import adapter_registry
from app.services.agents.tool_executor import execute_tool
from app.services.agents.workflows.workflow_signals import WorkflowSignalManager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select


class TaskExecutionError(RuntimeError):
    def __init__(self, code: str, message: Optional[str] = None, *, retryable: bool = False):
        super().__init__(message or code)
        self.code = code
        self.retryable = retryable
        self.message = message or code


@dataclass
class TaskExecutionContext:
    task: AgentTask
    plan: AgentPlan
    run: Any
    agent_def: Any
    execution_mode: str


@dataclass
class TaskExecutionResult:
    payload: Dict[str, Any]
    task_status: str = "completed"
    run_status: Optional[str] = None
    plan_status: Optional[str] = None
    event_type: Optional[str] = None
    event_payload: Optional[Dict[str, Any]] = None
    receipt_type: Optional[str] = None


class TaskEngine:
    def __init__(
        self,
        db: AsyncSession,
        *,
        llm_provider: Optional[AgentLLMProvider] = None,
        memory_service: Optional[AgentMemoryService] = None,
        handoff_service: Optional[AgentHandoffService] = None,
        signal_manager: Optional[WorkflowSignalManager] = None,
        receipt_service: Optional[AgentReceiptsService] = None,
        tool_executor: Callable[..., Awaitable[Dict[str, Any]]] = execute_tool,
    ):
        self.db = db
        self.settings = get_settings()
        self.compensation = CompensationService(db)
        self.memory = memory_service or AgentMemoryService(db)
        self.handoffs = handoff_service or AgentHandoffService(db)
        self.signals = signal_manager or WorkflowSignalManager(db)
        self.receipts = receipt_service or AgentReceiptsService(db)
        self.budgets = AgentBudgetService()
        self._llm_provider = llm_provider
        self._tool_executor = tool_executor
        self._handlers: dict[str, Callable[[TaskExecutionContext], Awaitable[TaskExecutionResult]]] = {
            "model_reasoning": self._handle_model_reasoning,
            "tool_call": self._handle_tool_call,
            "memory_read": self._handle_memory_read,
            "memory_write": self._handle_memory_write,
            "approval": self._handle_approval_wait,
            "approval_wait": self._handle_approval_wait,
            "handoff": self._handle_handoff,
            "workflow_signal": self._handle_workflow_signal,
            "final_response": self._handle_final_response,
        }
        self._contracts = {
            "model_reasoning": ModelReasoningTaskContractV1,
            "tool_call": ToolCallTaskContractV1,
            "memory_read": MemoryReadTaskContractV1,
            "memory_write": MemoryWriteTaskContractV1,
            "approval": ApprovalWaitTaskContractV1,
            "approval_wait": ApprovalWaitTaskContractV1,
            "handoff": HandoffTaskContractV1,
            "workflow_signal": WorkflowSignalTaskContractV1,
            "final_response": FinalResponseTaskContractV1,
        }

    async def execute_plan(self, plan_id: uuid.UUID):
        if not self.settings.agent_plan_execution_enabled:
            raise RuntimeError("Agent plan execution is disabled.")

        if self.settings.agent_stateful_workflows_enabled:
            from app.services.agents.workflows.workflow_engine import WorkflowEngine

            engine = WorkflowEngine(self.db)
            # Bridge point between task plans and workflows.
            _ = engine

        res = await self.db.execute(select(AgentPlan).where(AgentPlan.id == plan_id))
        plan = res.scalar_one_or_none()
        if not plan:
            raise ValueError("Plan not found")

        plan.status = "executing"
        await self.db.commit()

        while True:
            next_tasks = await self._get_ready_tasks(plan_id)
            if not next_tasks:
                res_all = await self.db.execute(select(AgentTask).where(AgentTask.plan_id == plan_id))
                all_tasks = res_all.scalars().all()
                if all(t.status == "completed" or t.status == "skipped" for t in all_tasks):
                    plan.status = "completed"
                    await self.db.commit()
                    break
                if any(t.status == "failed" for t in all_tasks):
                    plan.status = "failed"
                    await self.db.commit()
                    break
                break

            for task in next_tasks:
                await self.run_task(task.id)

    async def _get_ready_tasks(self, plan_id: uuid.UUID):
        stmt = select(AgentTask).where(AgentTask.plan_id == plan_id, AgentTask.status == "pending")
        res = await self.db.execute(stmt)
        pending = res.scalars().all()

        ready = []
        for task in pending:
            res_deps = await self.db.execute(
                select(AgentTask)
                .join(AgentTaskDependency, AgentTaskDependency.depends_on_task_id == AgentTask.id)
                .where(AgentTaskDependency.task_id == task.id)
            )
            deps = res_deps.scalars().all()
            if all(d.status == "completed" or d.status == "skipped" for d in deps):
                ready.append(task)
        return ready

    async def run_task(self, task_id: uuid.UUID):
        ctx = await self._load_context(task_id)
        if ctx is None:
            return

        retries_enabled = bool(self.settings.agent_auto_retry_enabled)
        max_attempts = max(1, ctx.task.max_attempts)

        while True:
            ctx.execution_mode = self._resolve_execution_mode()
            attempt = await self._start_attempt(ctx)
            step_number = (ctx.run.total_steps or 0) + 1
            checkpoint = await agent_state.create_run_checkpoint(
                self.db,
                ctx.run.id,
                step_number,
                {
                    "task_id": str(ctx.task.id),
                    "task_type": ctx.task.task_type,
                    "attempt_count": ctx.task.attempt_count,
                    "plan_id": str(ctx.plan.id),
                    "execution_mode": ctx.execution_mode,
                    "input_data": ctx.task.input_data,
                },
            )

            try:
                policy_result = await self._evaluate_policy(ctx)
                await self._validate_budget(ctx)
                started = time.monotonic()
                result = await self._execute_with_mode(ctx)
                latency_ms = int((time.monotonic() - started) * 1000)
                await self._record_success(
                    ctx,
                    attempt,
                    step_number,
                    checkpoint_id=checkpoint.id,
                    policy_result=policy_result,
                    result=result,
                    latency_ms=latency_ms,
                )
                break
            except Exception as exc:
                error = self._normalize_error(exc)
                await self._record_failure(
                    ctx,
                    attempt,
                    step_number,
                    checkpoint_id=checkpoint.id,
                    error=error,
                )
                if (
                    error.retryable
                    and retries_enabled
                    and ctx.task.attempt_count < max_attempts
                ):
                    ctx.task.status = "pending"
                    await self.db.commit()
                    continue
                break

    async def retry_task(self, task_id: uuid.UUID):
        res = await self.db.execute(select(AgentTask).where(AgentTask.id == task_id))
        task = res.scalar_one_or_none()
        if task:
            task.status = "pending"
            await self.db.commit()

    async def skip_task(self, task_id: uuid.UUID):
        res = await self.db.execute(select(AgentTask).where(AgentTask.id == task_id))
        task = res.scalar_one_or_none()
        if task:
            task.status = "skipped"
            await self.db.commit()

    async def _load_context(self, task_id: uuid.UUID) -> Optional[TaskExecutionContext]:
        res = await self.db.execute(select(AgentTask).where(AgentTask.id == task_id))
        task = res.scalar_one_or_none()
        if not task:
            return None

        res_plan = await self.db.execute(select(AgentPlan).where(AgentPlan.id == task.plan_id))
        plan = res_plan.scalar_one_or_none()
        if not plan:
            raise ValueError("Plan not found")

        run = await agent_state.get_agent_run(self.db, plan.agent_run_id)
        if not run:
            raise ValueError("Run not found")

        agent_def = await agent_state.get_agent_definition(self.db, run.agent_id)
        if not agent_def:
            raise ValueError("Agent definition not found")

        return TaskExecutionContext(
            task=task,
            plan=plan,
            run=run,
            agent_def=agent_def,
            execution_mode="real",
        )

    def _resolve_execution_mode(self) -> str:
        if getattr(self.settings, "agent_task_mock_mode", False):
            return "mock"
        if getattr(self.settings, "agent_task_dry_run_mode", False):
            return "dry_run"
        return "real"

    async def _start_attempt(self, ctx: TaskExecutionContext) -> AgentTaskAttempt:
        ctx.task.status = "running"
        ctx.task.attempt_count += 1
        attempt = AgentTaskAttempt(
            task_id=ctx.task.id,
            run_id=ctx.run.id,
            status="running",
            input_data=ctx.task.input_data,
            started_at=utc_now(),
        )
        self.db.add(attempt)
        await self.db.commit()
        await self.db.refresh(attempt)
        await self.db.refresh(ctx.task)
        await self.db.refresh(ctx.run)
        return attempt

    async def _evaluate_policy(self, ctx: TaskExecutionContext) -> Dict[str, Any]:
        from app.services.agents.agent_policy_engine import AgentPolicyEngine, PolicyRequest

        policy_req = PolicyRequest(
            action_type=ctx.task.task_type,
            subject=ctx.task.input_data.get("tool_name") or ctx.task.input_data.get("memory_type") or "task_engine",
            tenant_id=ctx.run.tenant_id,
            agent_id=ctx.run.agent_id,
            run_id=ctx.run.id,
            context={"plan_id": str(ctx.plan.id), "task_id": str(ctx.task.id)},
        )
        decision = await AgentPolicyEngine(self.db).evaluate_action_v2(policy_req)
        if decision.result == "deny":
            raise TaskExecutionError("policy_denied", f"Policy denial: {decision.reason}")
        return {
            "decision": decision.result,
            "reason": getattr(decision, "reason", None),
            "policy_id": str(getattr(decision, "id", "")) if getattr(decision, "id", None) else None,
        }

    async def _validate_budget(self, ctx: TaskExecutionContext) -> None:
        valid, reason = await self.budgets.validate_run_budget(ctx.agent_def, ctx.run)
        if not valid:
            raise TaskExecutionError("budget_exceeded", reason or "Budget exceeded")

    async def _execute_with_mode(self, ctx: TaskExecutionContext) -> TaskExecutionResult:
        if ctx.execution_mode == "mock":
            return self._mock_result(ctx)
        if ctx.execution_mode == "dry_run":
            return self._dry_run_result(ctx)
        if getattr(self.settings, "agent_task_simulation_mode", False):
            raise TaskExecutionError(
                "simulation_mode_unsupported",
                "AGENT_TASK_SIMULATION_MODE is not a real executor. Use AGENT_TASK_DRY_RUN_MODE or a real handler.",
            )
        handler = self._handlers.get(ctx.task.task_type)
        if handler is None:
            raise TaskExecutionError(
                "unsupported_task_type",
                f"Unsupported task type: {ctx.task.task_type}",
            )
        return await asyncio.wait_for(handler(ctx), timeout=self._resolve_timeout_seconds(ctx.task))

    def _mock_result(self, ctx: TaskExecutionContext) -> TaskExecutionResult:
        payload = {
            "status": "mock",
            "message": f"Mocked {ctx.task.task_type}",
            "mock": True,
        }
        return TaskExecutionResult(payload=payload)

    def _dry_run_result(self, ctx: TaskExecutionContext) -> TaskExecutionResult:
        payload = {
            "status": "simulated",
            "message": f"Dry-run simulation for {ctx.task.task_type}",
            "dry_run": True,
        }
        return TaskExecutionResult(payload=payload)

    def _resolve_timeout_seconds(self, task: AgentTask) -> float:
        input_data = task.input_data or {}
        requested = input_data.get("timeout_seconds")
        if isinstance(requested, (int, float)) and requested > 0:
            return float(requested)
        return 30.0

    def _normalize_error(self, exc: Exception) -> TaskExecutionError:
        if isinstance(exc, TaskExecutionError):
            return exc
        if isinstance(exc, ContractValidationError):
            return TaskExecutionError("contract_validation_failed", str(exc))
        if isinstance(exc, asyncio.TimeoutError):
            return TaskExecutionError("task_timeout", "Task execution timed out", retryable=True)
        return TaskExecutionError("operational_error", str(exc), retryable=True)

    async def _record_success(
        self,
        ctx: TaskExecutionContext,
        attempt: AgentTaskAttempt,
        step_number: int,
        *,
        checkpoint_id: uuid.UUID,
        policy_result: Dict[str, Any],
        result: TaskExecutionResult,
        latency_ms: int,
    ) -> None:
        output = dict(result.payload)
        output["execution_mode"] = ctx.execution_mode
        output["executor_name"] = "task_engine"
        output_hash = agent_state.compute_sha256(output)
        output["output_hash"] = output_hash

        receipt = await self.receipts.create_receipt(
            ctx.run.id,
            step_number,
            result.receipt_type or ctx.task.task_type,
            agent_state.compute_sha256(ctx.task.input_data),
            output_hash,
            metadata={
                "task_id": str(ctx.task.id),
                "attempt_id": str(attempt.id),
                "checkpoint_id": str(checkpoint_id),
                "execution_mode": ctx.execution_mode,
                "task_status": result.task_status,
            },
        )
        await self.db.flush()
        output["receipt_id"] = str(receipt.id)
        contract = self._contracts.get(ctx.task.task_type)
        if contract is None:
            raise TaskExecutionError(
                "unsupported_task_type",
                f"Unsupported task type: {ctx.task.task_type}",
            )
        contract.validate_output(
            {
                "execution_mode": ctx.execution_mode,
                "executor_name": "task_engine",
                "result": output,
            }
        )

        ctx.task.output_data = output
        ctx.task.status = result.task_status
        attempt.status = "completed"
        attempt.output_data = output
        attempt.completed_at = utc_now()

        if result.plan_status:
            ctx.plan.status = result.plan_status
        if result.run_status:
            ctx.run.status = result.run_status
            if result.run_status == "completed":
                ctx.run.completed_at = utc_now()
                ctx.run.output_hash = output_hash
                ctx.run.failure_reason = None
        if result.event_type:
            await agent_state.log_run_event(self.db, ctx.run.id, result.event_type, result.event_payload)

        await agent_state.log_run_step(
            self.db,
            ctx.run.id,
            step_number,
            ctx.task.task_type,
            ctx.task.input_data,
            output,
            "success",
            latency_ms=latency_ms,
            policy_result=policy_result,
            metadata={
                "task_id": str(ctx.task.id),
                "attempt_id": str(attempt.id),
                "checkpoint_id": str(checkpoint_id),
                "execution_mode": ctx.execution_mode,
                "receipt_id": str(receipt.id),
            },
        )
        await self.db.commit()

    async def _record_failure(
        self,
        ctx: TaskExecutionContext,
        attempt: AgentTaskAttempt,
        step_number: int,
        *,
        checkpoint_id: uuid.UUID,
        error: TaskExecutionError,
    ) -> None:
        output = {
            "status": "failed",
            "error_code": error.code,
            "failure_reason": error.message,
            "execution_mode": ctx.execution_mode,
            "executor_name": "task_engine",
        }
        output_hash = agent_state.compute_sha256(output)
        output["output_hash"] = output_hash

        receipt = await self.receipts.create_receipt(
            ctx.run.id,
            step_number,
            ctx.task.task_type,
            agent_state.compute_sha256(ctx.task.input_data),
            output_hash,
            metadata={
                "task_id": str(ctx.task.id),
                "attempt_id": str(attempt.id),
                "checkpoint_id": str(checkpoint_id),
                "execution_mode": ctx.execution_mode,
                "error_code": error.code,
            },
            success=False,
            failure_reason=error.message,
        )
        await self.db.flush()
        output["receipt_id"] = str(receipt.id)

        ctx.task.status = "failed"
        ctx.task.output_data = output
        attempt.status = "failed"
        attempt.output_data = output
        attempt.error = f"{error.code}: {error.message}"
        attempt.completed_at = utc_now()

        await agent_state.log_run_step(
            self.db,
            ctx.run.id,
            step_number,
            ctx.task.task_type,
            ctx.task.input_data,
            output,
            "failed",
            policy_result={"decision": "error", "reason": error.code},
            metadata={
                "task_id": str(ctx.task.id),
                "attempt_id": str(attempt.id),
                "checkpoint_id": str(checkpoint_id),
                "execution_mode": ctx.execution_mode,
                "receipt_id": str(receipt.id),
            },
            error=error.message,
        )

        await agent_state.log_run_event(
            self.db,
            ctx.run.id,
            "task_failed",
            {"task_id": str(ctx.task.id), "error_code": error.code, "failure_reason": error.message},
        )

        if ctx.task.compensation_action_id:
            await self.compensation.trigger_compensation(ctx.task.id)
        await self.db.commit()

    async def _handle_model_reasoning(self, ctx: TaskExecutionContext) -> TaskExecutionResult:
        data = ModelReasoningTaskContractV1.validate_input(ctx.task.input_data)
        provider = self._llm_provider or get_agent_llm_provider(self.db)
        response = await provider.generate(
            ctx.agent_def,
            ctx.run,
            allowed_tools=data.allowed_tools or ctx.agent_def.allowed_tools or [],
            input_override=data.prompt,
        )
        usage = response.usage if hasattr(response, "usage") else response.get("usage", {})
        cost_brl = response.cost_brl if hasattr(response, "cost_brl") else response.get("cost_brl", 0.0)
        ctx.run.total_tokens += usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
        ctx.run.estimated_cost_brl += float(cost_brl or 0.0)
        payload = response.to_dict() if hasattr(response, "to_dict") else dict(response)
        return TaskExecutionResult(payload=payload)

    async def _handle_tool_call(self, ctx: TaskExecutionContext) -> TaskExecutionResult:
        data = ToolCallTaskContractV1.validate_input(ctx.task.input_data)
        tool = await self._resolve_tool(data.tool_name)
        output = await self._tool_executor(
            db=self.db,
            tool=tool,
            parameters=data.parameters,
            run_id=ctx.run.id,
            tenant_id=ctx.run.tenant_id,
            agent_id=ctx.run.agent_id,
            is_dry_run=False,
        )
        ctx.run.tool_calls_count += 1
        return TaskExecutionResult(payload={"status": "success", "result": output})

    async def _resolve_tool(self, tool_name: str) -> AgentTool:
        res_tool = await self.db.execute(select(AgentTool).where(AgentTool.name == tool_name))
        tool = res_tool.scalar_one_or_none()
        if tool is not None:
            return tool

        adapter = adapter_registry.get_adapter(tool_name)
        if adapter is None:
            raise TaskExecutionError("tool_not_registered", f"Tool not registered: {tool_name}")

        tool = AgentTool(
            name=adapter.name,
            version=adapter.version,
            description=f"Ephemeral task tool for adapter {adapter.name}",
            category=adapter.to_registry_dict().get("category", "filesystem_safe"),
            input_schema_json=adapter.input_schema,
            output_schema_json=adapter.output_schema,
            side_effect_level=adapter.side_effect_level,
            timeout_seconds=30,
            rollback_supported=True,
            dry_run_supported=True,
            enabled=True,
        )
        self.db.add(tool)
        await self.db.flush()
        return tool

    async def _handle_memory_read(self, ctx: TaskExecutionContext) -> TaskExecutionResult:
        data = MemoryReadTaskContractV1.validate_input(ctx.task.input_data)
        items = await self.memory.read_memory(
            tenant_id=ctx.run.tenant_id,
            agent_id=ctx.run.agent_id,
            memory_type=data.memory_type,
            collection_id=data.collection_id,
            limit=data.limit,
            run_id=ctx.run.id,
        )
        ctx.run.memory_reads_count += 1
        return TaskExecutionResult(
            payload={
                "status": "success",
                "items": [
                    {
                        "id": str(item.id),
                        "memory_type": item.memory_type,
                        "summary": item.summary,
                        "content_hash": item.content_hash,
                        "created_at": item.created_at.isoformat(),
                    }
                    for item in items
                ],
            }
        )

    async def _handle_memory_write(self, ctx: TaskExecutionContext) -> TaskExecutionResult:
        data = MemoryWriteTaskContractV1.validate_input(ctx.task.input_data)
        item = await self.memory.write_memory(
            tenant_id=ctx.run.tenant_id,
            agent_id=ctx.run.agent_id,
            memory_type=data.memory_type,
            content=data.content,
            user_id=data.user_id,
            summary=data.summary,
            run_id=ctx.run.id,
            collection_id=data.collection_id,
        )
        return TaskExecutionResult(
            payload={
                "status": "success",
                "memory_item_id": str(item.id),
                "memory_type": item.memory_type,
                "retention_until": item.retention_until.isoformat(),
            }
        )

    async def _handle_approval_wait(self, ctx: TaskExecutionContext) -> TaskExecutionResult:
        data = ApprovalWaitTaskContractV1.validate_input(ctx.task.input_data)
        required, derived_risk, derived_reason, derived_role = await check_approval_required(
            self.db,
            ctx.run.id,
            data.tool_name,
            data.parameters,
        )
        if not required and not data.reason:
            raise TaskExecutionError("approval_not_required", "Approval wait requested but no approval is required.")

        request = await create_approval_request(
            self.db,
            run_id=ctx.run.id,
            tool_name=data.tool_name,
            tool_input=data.parameters,
            risk_level=data.risk_level or derived_risk,
            reason=data.reason or derived_reason,
            required_role=data.required_role or derived_role,
            step_number=(ctx.run.total_steps or 0) + 1,
            task_id=str(ctx.task.id),
        )
        return TaskExecutionResult(
            payload={
                "status": "waiting_approval",
                "approval_request_id": str(request.id),
                "tool_name": data.tool_name,
            },
            task_status="waiting_approval",
            run_status="waiting_approval",
            plan_status="waiting_approval",
            event_type="task_waiting_approval",
            event_payload={"task_id": str(ctx.task.id), "approval_request_id": str(request.id)},
            receipt_type="approval_wait",
        )

    async def _handle_handoff(self, ctx: TaskExecutionContext) -> TaskExecutionResult:
        data = HandoffTaskContractV1.validate_input(ctx.task.input_data)
        target_run_id = await self.handoffs.initiate_handoff(
            ctx.run.id,
            data.target_agent_id,
            data.reason,
            data.context,
        )
        return TaskExecutionResult(
            payload={"status": "success", "target_run_id": str(target_run_id)},
            event_type="task_handoff_completed",
            event_payload={"task_id": str(ctx.task.id), "target_run_id": str(target_run_id)},
        )

    async def _handle_workflow_signal(self, ctx: TaskExecutionContext) -> TaskExecutionResult:
        data = WorkflowSignalTaskContractV1.validate_input(ctx.task.input_data)
        signal = await self.signals.send_signal(data.workflow_run_id, data.signal_name, data.payload)
        return TaskExecutionResult(
            payload={"status": "success", "signal_id": str(signal.id), "signal_name": signal.signal_name},
            event_type="task_workflow_signal_sent",
            event_payload={"task_id": str(ctx.task.id), "signal_id": str(signal.id)},
        )

    async def _handle_final_response(self, ctx: TaskExecutionContext) -> TaskExecutionResult:
        data = FinalResponseTaskContractV1.validate_input(ctx.task.input_data)
        return TaskExecutionResult(
            payload={"status": "success", "final_output": data.output, "metadata": data.metadata},
            run_status="completed",
            plan_status="completed",
            event_type="run_completed",
            event_payload={"task_id": str(ctx.task.id)},
            receipt_type="final_response",
        )
