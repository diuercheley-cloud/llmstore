# Owner: agent-platform
import uuid
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.agents import AgentPlan, AgentTask, AgentTaskDependency, AgentTaskAttempt, AgentCompensationAction
from app.services.agents.compensation import CompensationService
from app.services.agents.agent_memory import AgentMemoryService
from app.services.agents.tool_executor import execute_tool
from app.services.agents.tool_adapter_registry import adapter_registry
from app.services.agents import agent_state

logger = logging.getLogger(__name__)

class TaskEngine:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.compensation = CompensationService(db)
        self.memory = AgentMemoryService(db)

    async def execute_plan(self, plan_id: uuid.UUID):
        if not self.settings.agent_plan_execution_enabled:
            raise RuntimeError("Agent plan execution is disabled.")

        if self.settings.agent_stateful_workflows_enabled:
            from app.services.agents.workflows.workflow_engine import WorkflowEngine
            engine = WorkflowEngine(self.db)
            # Logic to bridge plan to workflow could be here
            # For now we just log it as an architectural bridge
            logger.info(f"Delegating plan {plan_id} execution to stateful WorkflowEngine")

        res = await self.db.execute(select(AgentPlan).where(AgentPlan.id == plan_id))
        plan = res.scalar_one_or_none()
        if not plan:
            raise ValueError("Plan not found")

        plan.status = "executing"
        await self.db.commit()

        while True:
            # Find next tasks to execute (status='pending' and all dependencies 'completed')
            next_tasks = await self._get_ready_tasks(plan_id)
            if not next_tasks:
                # Check if all tasks are completed
                res_all = await self.db.execute(select(AgentTask).where(AgentTask.plan_id == plan_id))
                all_tasks = res_all.scalars().all()
                if all(t.status == "completed" or t.status == "skipped" for t in all_tasks):
                    plan.status = "completed"
                    await self.db.commit()
                    break
                elif any(t.status == "failed" for t in all_tasks):
                    plan.status = "failed"
                    await self.db.commit()
                    break
                else:
                    # Blocked or waiting approval
                    break

            for task in next_tasks:
                await self.run_task(task.id)

    async def _get_ready_tasks(self, plan_id: uuid.UUID) -> List[AgentTask]:
        # 1. Fetch pending tasks
        stmt = select(AgentTask).where(AgentTask.plan_id == plan_id, AgentTask.status == "pending")
        res = await self.db.execute(stmt)
        pending = res.scalars().all()
        
        ready = []
        for task in pending:
            # 2. Check dependencies
            res_deps = await self.db.execute(
                select(AgentTask).join(AgentTaskDependency, AgentTaskDependency.depends_on_task_id == AgentTask.id)
                .where(AgentTaskDependency.task_id == task.id)
            )
            deps = res_deps.scalars().all()
            if all(d.status == "completed" or d.status == "skipped" for d in deps):
                ready.append(task)
        
        return ready

    async def run_task(self, task_id: uuid.UUID):
        res = await self.db.execute(select(AgentTask).where(AgentTask.id == task_id))
        task = res.scalar_one_or_none()
        if not task:
            return

        # Fetch plan and run for context
        res_plan = await self.db.execute(select(AgentPlan).where(AgentPlan.id == task.plan_id))
        plan = res_plan.scalar_one_or_none()
        run = await agent_state.get_agent_run(self.db, plan.agent_run_id)
        agent_def = await agent_state.get_agent_definition(self.db, run.agent_id)

        task.status = "running"
        task.attempt_count += 1
        await self.db.commit()

        attempt = AgentTaskAttempt(
            task_id=task.id,
            run_id=run.id,
            status="running",
            input_data=task.input_data,
            started_at=utc_now()
        )
        self.db.add(attempt)

        # 0. Policy Engine Check (v2)
        from app.services.agents.agent_policy_engine import AgentPolicyEngine, PolicyRequest
        policy_req = PolicyRequest(
            action_type=task.task_type,
            subject=task.input_data.get("tool_name") or task.input_data.get("memory_type") or "task_engine",
            tenant_id=run.tenant_id,
            agent_id=run.agent_id,
            run_id=run.id,
            context={"plan_id": str(plan.id), "task_id": str(task.id)}
        )
        policy_engine = AgentPolicyEngine(self.db)
        decision = await policy_engine.evaluate_action_v2(policy_req)
        
        if decision.result == "deny":
            task.status = "failed"
            attempt.status = "failed"
            attempt.error = f"Policy denial: {decision.reason}"
            attempt.completed_at = utc_now()
            await self.db.commit()
            return

        await self.db.commit()

        try:
            output = {}
            if not self.settings.agent_planner_real_execution_enabled:
                output = {"status": "simulated", "message": f"Simulated {task.task_type}"}
            else:
                if task.task_type == "model_reasoning":
                    from app.services.agents.agent_llm_provider import get_agent_llm_provider
                    provider = get_agent_llm_provider(self.db)
                    decision = await provider.generate(
                        agent_def,
                        run,
                        allowed_tools=agent_def.allowed_tools or [],
                        input_override=task.input_data.get("prompt"),
                    )
                    output = decision.to_dict() if hasattr(decision, "to_dict") else decision
                
                elif task.task_type == "tool_call":
                    from app.models.agents import AgentTool
                    tool_name = task.input_data.get("tool_name")
                    stmt_tool = select(AgentTool).where(AgentTool.name == tool_name)
                    res_tool = await self.db.execute(stmt_tool)
                    tool = res_tool.scalar_one_or_none()
                    if tool is None:
                        adapter = adapter_registry.get_adapter(tool_name)
                        if adapter is not None:
                            tool = AgentTool(
                                name=adapter.name,
                                version=adapter.version,
                                description=f"Ephemeral tool generated from adapter {adapter.name}",
                                category=adapter.to_registry_dict().get("category", "filesystem_safe"),
                                input_schema_json=adapter.input_schema,
                                output_schema_json=adapter.output_schema,
                                side_effect_level=adapter.side_effect_level,
                                timeout_seconds=30,
                                rollback_supported=True,
                                dry_run_supported=True,
                                enabled=True,
                            )
                        else:
                            tool = AgentTool(
                                name=tool_name,
                                version="0.0.0-ephemeral",
                                description=f"Ephemeral task tool for {tool_name}",
                                category="filesystem_safe",
                                input_schema_json={"type": "object"},
                                output_schema_json={"type": "object"},
                                side_effect_level="none",
                                timeout_seconds=30,
                                rollback_supported=False,
                                dry_run_supported=True,
                                enabled=True,
                            )
                    
                    output = await execute_tool(
                        db=self.db,
                        tool=tool,
                        parameters=task.input_data.get("parameters", {}),
                        run_id=run.id,
                        tenant_id=run.tenant_id
                    )
                
                elif task.task_type == "memory_read":
                    output = await self.memory.read_memory(
                        tenant_id=run.tenant_id,
                        agent_id=run.agent_id,
                        memory_type=task.input_data.get("memory_type", "short_term"),
                        run_id=run.id
                    )
                
                elif task.task_type == "memory_write":
                    await self.memory.write_memory(
                        tenant_id=run.tenant_id,
                        agent_id=run.agent_id,
                        memory_type=task.input_data.get("memory_type", "short_term"),
                        content=task.input_data.get("content"),
                        summary=task.input_data.get("summary"),
                        run_id=run.id
                    )
                    output = {"status": "written"}

                elif task.task_type == "approval":
                    from app.services.agents.human_approval import create_approval_request
                    await create_approval_request(
                        db=self.db,
                        run_id=run.id,
                        tool_name=task.input_data.get("tool_name"),
                        tool_input=task.input_data.get("parameters"),
                        reason="Planner identified high-risk task",
                        step_number=run.total_steps
                    )
                    
                    if self.settings.agent_stateful_workflows_enabled:
                        # In stateful mode, we don't just set status, we might want to 
                        # create a specific wait condition or signal
                        logger.info(f"Task {task.id} entering stateful approval wait")
                    
                    task.status = "waiting_approval"
                    plan.status = "waiting_approval"
                    await self.db.commit()
                    return

            task.output_data = output
            task.status = "completed"
            attempt.status = "completed"
            attempt.output_data = output
            attempt.completed_at = utc_now()

        except Exception as e:
            logger.exception(f"Task {task_id} failed")
            task.status = "failed"
            attempt.status = "failed"
            attempt.error = str(e)
            attempt.completed_at = utc_now()
            
            if task.compensation_action_id:
                await self.compensation.trigger_compensation(task.id)
            
            if self.settings.agent_auto_retry_enabled and task.attempt_count < task.max_attempts:
                task.status = "pending"
                if self.settings.agent_replan_enabled:
                    # Logic to trigger replan could be here
                    pass
        
        await self.db.commit()

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
