# Owner: agent-platform
import logging
import uuid
from datetime import timedelta
from typing import Any

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.agents.agent_workflows import AgentWorkflowDefinition, AgentWorkflowRun
from app.services.agents.workflows.subworkflow_runtime import SubworkflowRuntime
from app.services.agents.workflows.workflow_branching import WorkflowBranchingManager
from app.services.agents.workflows.workflow_dag import WorkflowDAG
from app.services.agents.workflows.workflow_locks import WorkflowLockManager
from app.services.agents.workflows.workflow_parallel import WorkflowParallelManager
from app.services.agents.workflows.workflow_signals import WorkflowSignalManager
from app.services.agents.workflows.workflow_state_machine import (
    WorkflowStateMachine,
    WorkflowStatus,
)
from app.services.agents.workflows.workflow_timers import WorkflowTimerManager
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """
    Main orchestration engine for stateful workflows.
    Handles run lifecycle, persistence, and execution of workflow steps.
    Supports both legacy state machines and modern DAGs.
    """

    def __init__(self, db: AsyncSession, worker_id: str = "default_worker"):
        self.db = db
        self.worker_id = worker_id
        self.settings = get_settings()
        self.locks = WorkflowLockManager(db)

    async def create_run(
        self,
        workflow_id: uuid.UUID | None = None,
        workflow_definition_id: uuid.UUID | None = None,
        tenant_id: str = "",
        input_data: dict[str, Any] = None,
    ) -> AgentWorkflowRun:
        run = AgentWorkflowRun(
            workflow_id=workflow_id,
            workflow_definition_id=workflow_definition_id,
            tenant_id=tenant_id,
            status=WorkflowStatus.CREATED.value,
            current_state="start",
            state_data={},
            context=input_data or {},
            next_execution_at=utc_now(),
        )
        self.db.add(run)
        await self.db.commit()
        return run

    def _legacy_state_machine(self, run: AgentWorkflowRun) -> dict[str, dict[str, Any]]:
        context = run.context or {}
        if context.get("requires_approval"):
            return {
                "start": {"action": "handoff", "next_state": "process"},
                "process": {"action": "wait_approval", "resume_to_state": "end"},
                "end": {"action": "complete", "result": "approval completed"},
            }
        if context.get("sleep_seconds"):
            return {
                "start": {"action": "handoff", "next_state": "process"},
                "process": {
                    "action": "sleep",
                    "seconds": int(context["sleep_seconds"]),
                    "timer_name": "legacy_sleep",
                    "resume_to_state": "end",
                },
                "end": {"action": "complete", "result": "sleep completed"},
            }
        return {
            "start": {"action": "handoff", "next_state": "process"},
            "process": {"action": "complete", "result": "workflow completed"},
        }

    def _resolve_state_machine(self, run: AgentWorkflowRun) -> dict[str, dict[str, Any]]:
        context = run.context or {}
        definition = context.get("state_machine")
        if isinstance(definition, dict) and definition:
            return definition
        return self._legacy_state_machine(run)

    async def _migrate_run_definition(self, run: AgentWorkflowRun) -> None:
        context = run.context or {}
        current_version = context.get("workflow_version")
        target_version = context.get("target_workflow_version")
        migrations = context.get("state_migrations", {})
        if not current_version or not target_version or current_version == target_version:
            return

        migration = migrations.get(f"{current_version}->{target_version}")
        if not migration:
            raise ValueError(
                f"No workflow migration defined for {current_version} -> {target_version}"
            )

        state_mapping = migration.get("state_mapping", {})
        if run.current_state in state_mapping:
            state_event = WorkflowStateMachine(run).set_current_state(
                state_mapping[run.current_state]
            )
            self.db.add(state_event)

        context_updates = migration.get("context_updates", {})
        merged_context = dict(run.context or {})
        merged_context.update(context_updates)
        merged_context["workflow_version"] = target_version
        run.context = merged_context
        run.state_data = {
            **(run.state_data or {}),
            "migration_applied": {
                "from_version": current_version,
                "to_version": target_version,
            },
        }

    async def _apply_compensation(self, run: AgentWorkflowRun, reason: str) -> None:
        state_machine = self._resolve_state_machine(run)
        current_state = run.current_state
        state_config = state_machine.get(current_state, {})
        compensation = state_config.get("compensation")
        if not compensation:
            return

        state_data = dict(run.state_data or {})
        log = list(state_data.get("compensation_log", []))
        entry = {
            "state": current_state,
            "reason": reason,
            "action": compensation.get("action", "record_only"),
            "applied_at": utc_now().isoformat(),
        }
        if compensation.get("action") == "set_context":
            merged_context = dict(run.context or {})
            merged_context.update(compensation.get("updates", {}))
            run.context = merged_context
            entry["updates"] = compensation.get("updates", {})
        state_data["compensation_log"] = log + [entry]
        run.state_data = state_data

    async def _consume_next_signal(self, run: AgentWorkflowRun, sm: WorkflowStateMachine) -> bool:
        signals = WorkflowSignalManager(self.db)
        pending = await signals.get_pending_signals(run.id)
        if not pending:
            return False

        expected_signal = (run.state_data or {}).get("expected_signal")
        signal = next(
            (
                item
                for item in pending
                if expected_signal is None or item.signal_name == expected_signal
            ),
            None,
        )
        if signal is None:
            return False
        await signals.consume_signal(signal.id)
        sm.update_context(
            {
                "last_signal": {
                    "id": str(signal.id),
                    "name": signal.signal_name,
                    "payload": signal.payload,
                }
            }
        )
        resume_to_state = (run.state_data or {}).get("resume_to_state")
        if resume_to_state:
            self.db.add(sm.set_current_state(resume_to_state))
            sm.update_state_data(
                {"resume_to_state": None, "waiting_on": None, "expected_signal": None}
            )
        if run.status in {
            WorkflowStatus.WAITING_SIGNAL.value,
            WorkflowStatus.WAITING_APPROVAL.value,
            WorkflowStatus.SLEEPING.value,
            WorkflowStatus.WAITING_WEBHOOK.value,
        }:
            self.db.add(
                await sm.transition_to(
                    WorkflowStatus.RUNNING,
                    payload={"resume_signal": signal.signal_name},
                )
            )
        return True

    async def process_ready_runs(self):
        """
        Finds and processes workflow runs that are ready for execution.
        """
        if not self.settings.agent_stateful_workflows_enabled:
            return

        stmt = (
            select(AgentWorkflowRun)
            .where(
                AgentWorkflowRun.status.in_(
                    [
                        WorkflowStatus.CREATED.value,
                        WorkflowStatus.RUNNING.value,
                        WorkflowStatus.RETRY_SCHEDULED.value,
                    ]
                ),
                AgentWorkflowRun.next_execution_at <= utc_now(),
            )
            .order_by(AgentWorkflowRun.next_execution_at.asc())
            .limit(10)
            .with_for_update(skip_locked=True)
        )

        res = await self.db.execute(stmt)
        runs = res.scalars().all()

        for run in runs:
            await self.execute_step(run.id)

    async def execute_step(self, run_id: uuid.UUID):
        """
        Executes a single step of a workflow run with distributed locking.
        """
        lock_key = f"workflow_run:{run_id}"
        owner_id = uuid.uuid5(uuid.NAMESPACE_DNS, self.worker_id)
        if not await self.locks.acquire_lock(lock_key, owner_id):
            return

        try:
            stmt = select(AgentWorkflowRun).where(AgentWorkflowRun.id == run_id)
            res = await self.db.execute(stmt)
            run = res.scalar_one_or_none()
            if not run:
                return

            await self._migrate_run_definition(run)

            sm = WorkflowStateMachine(run)
            self.db.add(await sm.transition_to(WorkflowStatus.RUNNING))
            await self.db.commit()

            await self._execute_workflow_logic(run, sm)

            await self.db.commit()
        except Exception as e:
            logger.exception(f"Error executing workflow {run_id}")
            await self.db.rollback()
            # Handle failure, retries, etc.
            await self._handle_failure(run_id, e)
        finally:
            await self.locks.release_lock(lock_key, owner_id)

    async def _execute_dag_logic(self, run: AgentWorkflowRun, sm: WorkflowStateMachine):
        """
        Executes logic for a DAG-based workflow.
        """
        from app.models.agents.agent_workflows import (
            AgentWorkflowNode,  # local import to avoid circular dependency if any
        )

        # Load definition
        stmt = select(AgentWorkflowDefinition).where(
            AgentWorkflowDefinition.id == run.workflow_definition_id
        )
        res = await self.db.execute(stmt)
        definition = res.scalar_one_or_none()
        if not definition:
            raise ValueError(f"Workflow definition {run.workflow_definition_id} not found")

        dag = WorkflowDAG(definition)
        context = sm.get_context()

        # Determine current nodes to process
        if run.current_state == "start":
            current_node_keys = [n for n, d in dag.graph.in_degree() if d == 0]
        else:
            current_node_keys = (run.state_data or {}).get("active_nodes", [])

        if not current_node_keys:
            self.db.add(await sm.transition_to(WorkflowStatus.COMPLETED))
            return

        next_active_nodes = []
        for node_key in current_node_keys:
            node_data = dag.graph.nodes[node_key]
            node_type = node_data["type"]
            node_config = node_data.get("config", {})

            if node_type == "task":
                logger.info(f"Executing task node: {node_key}")
                successors = dag.get_next_nodes(node_key, context)
                next_active_nodes.extend(successors)

            elif node_type == "condition":
                branch_manager = WorkflowBranchingManager(run)
                next_node = branch_manager.resolve_branch(node_config, context)
                if next_node:
                    next_active_nodes.append(next_node)

            elif node_type == "parallel_fanout":
                parallel_manager = WorkflowParallelManager(self.db, run)
                successors = list(dag.graph.successors(node_key))
                await parallel_manager.create_parallel_group(
                    node=AgentWorkflowNode(
                        node_key=node_key, node_type=node_type, config=node_config
                    ),
                    branches_count=len(successors),
                )
                next_active_nodes.extend(successors)

            elif node_type == "fanin_join":
                parallel_manager = WorkflowParallelManager(self.db, run)
                preds = dag.get_dependencies(node_key)
                is_ready = True
                completed_nodes = (run.state_data or {}).get("completed_nodes", [])
                for pred in preds:
                    if pred not in completed_nodes:
                        is_ready = False
                        break

                if is_ready:
                    successors = list(dag.graph.successors(node_key))
                    next_active_nodes.extend(successors)
                else:
                    next_active_nodes.append(node_key)

            elif node_type == "subworkflow":
                sub_runtime = SubworkflowRuntime(self.db, run)
                if not await sub_runtime.is_subworkflow_complete(node_key):
                    sub_def_id = uuid.UUID(node_config["subworkflow_definition_id"])
                    await sub_runtime.start_subworkflow(node_key, sub_def_id, context)
                    next_active_nodes.append(node_key)
                else:
                    results = await sub_runtime.get_subworkflow_results(node_key)
                    sm.update_context({f"subworkflow_{node_key}": results})
                    successors = list(dag.graph.successors(node_key))
                    next_active_nodes.extend(successors)

            elif node_type == "approval":
                sm.update_state_data(
                    {
                        "waiting_on": f"approval:{node_key}",
                        "expected_signal": f"approval_{node_key}",
                    }
                )
                self.db.add(await sm.transition_to(WorkflowStatus.WAITING_APPROVAL))
                next_active_nodes.append(node_key)
                break

            elif node_type == "timer":
                delay = node_config.get("seconds", 60)
                run.next_execution_at = utc_now() + timedelta(seconds=delay)
                self.db.add(await sm.transition_to(WorkflowStatus.SLEEPING))
                next_active_nodes.append(node_key)
                break

            elif node_type == "webhook_wait":
                webhook_id = node_config.get("webhook_id")
                sm.update_state_data({"waiting_on": f"webhook:{webhook_id}"})
                self.db.add(await sm.transition_to(WorkflowStatus.WAITING_WEBHOOK))
                next_active_nodes.append(node_key)
                break

        next_active_nodes = list(set(next_active_nodes))
        completed_nodes = list(
            set((run.state_data or {}).get("completed_nodes", []) + current_node_keys)
        )
        remaining_active = [n for n in next_active_nodes if n not in completed_nodes]

        sm.update_state_data({"active_nodes": remaining_active, "completed_nodes": completed_nodes})

        if not remaining_active:
            self.db.add(await sm.transition_to(WorkflowStatus.COMPLETED))
        else:
            run.current_state = "processing"

    async def _execute_workflow_logic(self, run: AgentWorkflowRun, sm: WorkflowStateMachine):
        if run.workflow_definition_id:
            await self._execute_dag_logic(run, sm)
            return

        await self._consume_next_signal(run, sm)

        context = sm.get_context()
        current_state = run.current_state
        state_machine = self._resolve_state_machine(run)
        state_config = state_machine.get(current_state)
        if not state_config:
            raise ValueError(f"Workflow state '{current_state}' is not defined")

        action = state_config.get("action", "complete")
        sm.update_state_data(
            {
                "last_processed_state": current_state,
                "state_machine_mode": "declarative",
            }
        )

        if action == "handoff":
            next_state = state_config.get("next_state")
            if not next_state:
                raise ValueError(f"State '{current_state}' requires next_state for handoff")
            self.db.add(sm.set_current_state(next_state))
            sm.update_state_data(
                {
                    "last_handoff": {"from": current_state, "to": next_state},
                    "resume_to_state": None,
                }
            )
            sm.update_context({"step": context.get("step", 0) + 1})
            self.db.add(
                await sm.transition_to(
                    WorkflowStatus.RUNNING,
                    payload={
                        "action": "handoff",
                        "from_state": current_state,
                        "to_state": next_state,
                    },
                )
            )
            return

        if action == "sleep":
            delay_seconds = int(state_config.get("seconds", 0))
            if delay_seconds <= 0:
                raise ValueError(f"State '{current_state}' requires positive seconds for sleep")
            timer_name = state_config.get("timer_name", current_state)
            next_state = (
                state_config.get("resume_to_state")
                or state_config.get("next_state")
                or current_state
            )
            run.next_execution_at = utc_now() + timedelta(seconds=delay_seconds)
            sm.update_state_data(
                {"resume_to_state": next_state, "waiting_on": f"timer:{timer_name}"}
            )
            timers = WorkflowTimerManager(self.db)
            await timers.create_timer(run.id, timer_name, delay_seconds)
            self.db.add(
                await sm.transition_to(
                    WorkflowStatus.SLEEPING,
                    payload={
                        "action": "sleep",
                        "seconds": delay_seconds,
                        "resume_to_state": next_state,
                    },
                )
            )
            return

        if action == "wait_signal":
            expected_signal = state_config.get("signal")
            next_state = state_config.get("resume_to_state") or state_config.get("next_state")
            sm.update_state_data(
                {
                    "expected_signal": expected_signal,
                    "resume_to_state": next_state,
                    "waiting_on": "signal",
                }
            )
            self.db.add(
                await sm.transition_to(
                    WorkflowStatus.WAITING_SIGNAL,
                    payload={"action": "wait_signal", "expected_signal": expected_signal},
                )
            )
            return

        if action == "wait_approval":
            next_state = state_config.get("resume_to_state") or state_config.get("next_state")
            sm.update_state_data({"resume_to_state": next_state, "waiting_on": "approval"})
            self.db.add(
                await sm.transition_to(
                    WorkflowStatus.WAITING_APPROVAL,
                    payload={"action": "wait_approval", "resume_to_state": next_state},
                )
            )
            return

        if action == "complete":
            result = (
                state_config.get("result")
                or context.get("result")
                or f"Workflow completed in state '{current_state}'"
            )
            next_state = state_config.get("next_state")
            if next_state:
                self.db.add(sm.set_current_state(next_state))
            sm.update_state_data({"result": result, "completed_state": current_state})
            self.db.add(
                await sm.transition_to(
                    WorkflowStatus.COMPLETED,
                    payload={"action": "complete", "result": result},
                )
            )
            return

        if action == "fail":
            raise RuntimeError(
                state_config.get("reason", f"Workflow failed in state '{current_state}'")
            )

        raise ValueError(f"Unsupported workflow action '{action}'")

    async def _handle_failure(self, run_id: uuid.UUID, error: Exception):
        stmt = select(AgentWorkflowRun).where(AgentWorkflowRun.id == run_id)
        res = await self.db.execute(stmt)
        run = res.scalar_one_or_none()
        if run:
            await self._apply_compensation(run, str(error))
            run.retry_count += 1
            if run.retry_count >= run.max_retries:
                run.status = WorkflowStatus.FAILED.value
                # Move to DLQ logic could be here
            else:
                run.status = WorkflowStatus.RETRY_SCHEDULED.value
                run.next_execution_at = utc_now() + timedelta(minutes=2**run.retry_count)
            await self.db.commit()

    async def signal_run(self, run_id: uuid.UUID, signal_name: str, payload: dict[str, Any]):
        from app.services.agents.workflows.workflow_signals import WorkflowSignalManager

        signals = WorkflowSignalManager(self.db)
        await signals.send_signal(run_id, signal_name, payload)

    async def cancel_run(self, run_id: uuid.UUID):
        stmt = select(AgentWorkflowRun).where(AgentWorkflowRun.id == run_id)
        res = await self.db.execute(stmt)
        run = res.scalar_one_or_none()
        if run:
            await self._apply_compensation(run, "cancelled")
            sm = WorkflowStateMachine(run)
            self.db.add(await sm.transition_to(WorkflowStatus.CANCELLED))
            await self.db.commit()
