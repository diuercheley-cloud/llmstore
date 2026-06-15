import json
import logging
import re
from typing import Any

from .coding_loop import CodingLoop
from .mas.blackboard import Blackboard
from .mas.registry import AgentRegistry
from .model_router import ModelRouter
from .models import ExecutionResult

logger = logging.getLogger(__name__)


def _safe_parse_json(content: str) -> dict[str, Any] | list[Any] | None:
    if not content or not content.strip():
        return None

    cleaned = content.strip()

    # 1. Try direct parse
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, (dict, list)):
            return parsed
    except json.JSONDecodeError:
        pass

    # 2. Extract from json code fence
    for pattern in [r"```json\s*\n?(.*?)\n?```", r"```\s*\n?(.*?)\n?```"]:
        match = re.search(pattern, cleaned, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(1).strip())
                if isinstance(parsed, (dict, list)):
                    return parsed
            except json.JSONDecodeError:
                pass

    # 3. Find first JSON object or array using raw_decode
    decoder = json.JSONDecoder()
    for start, char in enumerate(cleaned):
        if char not in ("{", "["):
            continue
        try:
            obj, end = decoder.raw_decode(cleaned[start:])
            if isinstance(obj, (dict, list)):
                return obj
        except json.JSONDecodeError:
            continue

    # 4. If it looks like a JSON dict with single quotes, try replacing
    if cleaned.startswith("{") and cleaned.endswith("}"):
        try:
            normalized = cleaned.replace("'", '"')
            normalized = re.sub(r"(?<!\\)\\(?![\"\\/bfnrtu])", "", normalized)
            parsed = json.loads(normalized)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    return None


class MultiAgentOrchestrator:
    def __init__(self, coding_loop: CodingLoop):
        self.coding_loop = coding_loop
        self.agent_client = coding_loop.agent_client
        self.config = getattr(coding_loop, "config", None)
        if self.config is None:
            from .config import HarnessConfig

            self.config = HarnessConfig(
                code_agent=getattr(self.agent_client, "agent_id", "default-coder"),
                provider=getattr(self.agent_client, "provider", "stub"),
                model=getattr(self.agent_client, "model", ""),
                base_url=getattr(self.agent_client, "base_url", ""),
            )
        self.router = ModelRouter(self.config)
        self.registry = AgentRegistry.load(self.config.agent_registry_file)

    def generate_orchestration_report(self, blackboard: Blackboard) -> str:
        lines = [
            "# Orchestration Report",
            f"**Task:** {blackboard.state.task}",
            "",
            "## Sub-task Summary",
            "| ID | Description | Status | Assigned To |",
            "|---|---|---|---|",
        ]
        for st in blackboard.state.sub_tasks:
            lines.append(
                f"| {st.id} | {st.description} | {st.status.upper()} | {st.assigned_to or '-'} |"
            )

        lines.append("")
        lines.append("## Agent Dialog")
        for msg in blackboard.state.messages:
            lines.append(f"### From: {msg.sender} -> To: {msg.recipient}")
            lines.append(f"**Timestamp:** {msg.timestamp}")
            lines.append("")
            lines.append(msg.content)
            if msg.metadata:
                lines.append("")
                lines.append("<details><summary>Metadata</summary>")
                try:
                    meta_str = json.dumps(msg.metadata, indent=2, default=str)
                except Exception:
                    meta_str = str(msg.metadata)
                lines.append(f"```json\n{meta_str}\n```")
                lines.append("</details>")
            lines.append("")
            lines.append("---")

        return "\n".join(lines)

    async def _call_llm_json(
        self,
        prompt: str,
        task_type: str = "supervisor",
        profile_name: str | None = None,
    ) -> dict[str, Any] | list[Any] | None:
        messages = [{"role": "user", "content": prompt}]

        cfg_override = {}
        if hasattr(self.config, "max_tokens") and self.config.max_tokens:
            cfg_override["max_tokens"] = self.config.max_tokens

        response = await self.router.chat_completion_with_fallback(
            messages,
            task_type=task_type,
            profile_name=profile_name,
            plain_chat=True,
        )
        content = response["choices"][0]["message"]["content"]
        parsed = _safe_parse_json(content)
        if parsed is not None:
            return parsed

        logger.warning(
            "LLM returned invalid JSON for %s. Content: %.200s",
            task_type,
            content,
        )
        return None

    async def run_supervisor(
        self, task: str | list[dict[str, Any]], max_steps: int = 20
    ) -> ExecutionResult:
        task_str = json.dumps(task) if isinstance(task, list) else task
        blackboard = Blackboard(task_str)

        logger.info("Starting Supervisor Orchestration")

        last_agent = None
        same_agent_count = 0
        last_subtask_ids: set[str] = set()

        for i in range(max_steps):
            logger.info("Supervisor Step %d/%d", i + 1, max_steps)

            decision = await self._call_supervisor(task_str, blackboard)

            if decision is None:
                logger.warning(
                    "Supervisor returned no valid decision; forcing continue with developer"
                )
                decision = {
                    "next_agent": "developer",
                    "instruction": "Continue with the task",
                    "type": "action",
                }

            if "sub_tasks" in decision:
                for st_data in decision["sub_tasks"]:
                    from .mas.schemas import SubTask

                    try:
                        st = SubTask(**st_data)
                        blackboard.update_sub_task(st)
                    except Exception as e:
                        logger.warning("Failed to parse sub-task data: %s", e)

            next_agent_id = decision.get("next_agent")
            instruction = decision.get("instruction", "")

            if next_agent_id == "final" or decision.get("type") == "final":
                logger.info("Supervisor decided to finish")
                msg = decision.get("message", "Task completed")
                return ExecutionResult(
                    success=True,
                    message=msg,
                    events=[
                        {
                            "event": "multi_agent.dialog",
                            "messages": [
                                m.model_dump(mode="json") for m in blackboard.state.messages
                            ],
                        },
                        {
                            "event": "multi_agent.report",
                            "report": self.generate_orchestration_report(blackboard),
                        },
                    ],
                )

            if not next_agent_id or next_agent_id not in self.registry.agents:
                logger.warning("Supervisor returned invalid agent: %s", next_agent_id)
                if "sub_tasks" in decision:
                    continue
                next_agent_id = "developer"

            # Cycle detection
            if next_agent_id == last_agent:
                same_agent_count += 1
            else:
                same_agent_count = 0
            last_agent = next_agent_id

            if same_agent_count >= 3:
                logger.warning(
                    "Supervisor called '%s' 3 times in a row. "
                    "Assuming task is stuck. Forcing finish.",
                    next_agent_id,
                )
                return ExecutionResult(
                    success=False,
                    error=f"Supervisor stuck calling '{next_agent_id}' repeatedly. Cycle detected.",
                    events=[
                        {
                            "event": "multi_agent.dialog",
                            "messages": [
                                m.model_dump(mode="json") for m in blackboard.state.messages
                            ],
                        },
                        {
                            "event": "multi_agent.report",
                            "report": self.generate_orchestration_report(blackboard),
                        },
                    ],
                )

            # Detect stalled sub-tasks
            current_subtask_ids = {st.id for st in blackboard.state.sub_tasks}
            if current_subtask_ids and current_subtask_ids == last_subtask_ids:
                all_completed = all(
                    st.status in ("completed", "failed") for st in blackboard.state.sub_tasks
                )
                if all_completed:
                    logger.info("All sub-tasks completed. Finishing.")
                    return ExecutionResult(
                        success=True,
                        message="All sub-tasks completed",
                        events=[
                            {
                                "event": "multi_agent.dialog",
                                "messages": [
                                    m.model_dump(mode="json") for m in blackboard.state.messages
                                ],
                            },
                            {
                                "event": "multi_agent.report",
                                "report": self.generate_orchestration_report(blackboard),
                            },
                        ],
                    )
            last_subtask_ids = current_subtask_ids

            logger.info("Supervisor delegated to: %s", next_agent_id)
            agent_def = self.registry.get_agent(next_agent_id)

            blackboard.add_message(
                "Supervisor",
                next_agent_id,
                f"Delegated task: {instruction}",
                {"agent_role": agent_def.role if agent_def else None},
            )

            self.coding_loop.current_agent = next_agent_id

            result = await self.coding_loop.run(
                instruction,
                system_override=agent_def.prompt if agent_def else None,
                model_profile_override=agent_def.model_profile if agent_def else None,
            )

            # Enrich blackboard with execution result
            changed_files = result.metrics.get("changed_files", []) if result.metrics else []
            blackboard.record_changes(changed_files)
            blackboard.set_custom_state("last_result_success", result.success)
            blackboard.set_custom_state("last_result_error", result.error)
            blackboard.set_custom_state("last_result_message", result.message)
            blackboard.set_custom_state("last_changed_files", changed_files)
            blackboard.set_custom_state("last_agent_id", next_agent_id)

            blackboard.add_message(
                next_agent_id,
                "Supervisor",
                f"Completed: {result.message}",
                {
                    "success": result.success,
                    "changed_files": changed_files,
                    "error": result.error,
                },
            )

            # Mark the relevant sub-task as completed/failed
            for st in blackboard.state.sub_tasks:
                if st.assigned_to == next_agent_id and st.status in ("pending", "in_progress"):
                    st.status = "completed" if result.success else "failed"
                    st.result = result.message
                    break

        return ExecutionResult(
            success=False,
            error="Reached maximum number of supervisor steps",
            events=[
                {
                    "event": "multi_agent.dialog",
                    "messages": [m.model_dump(mode="json") for m in blackboard.state.messages],
                },
                {
                    "event": "multi_agent.report",
                    "report": self.generate_orchestration_report(blackboard),
                },
            ],
        )

    async def _call_supervisor(self, task: str, blackboard: Blackboard) -> dict[str, Any] | None:
        supervisor_def = self.registry.get_agent("supervisor")
        available_agents = [
            {"id": k, "role": v.role, "description": v.description}
            for k, v in self.registry.agents.items()
            if k != "supervisor"
        ]

        custom_state = blackboard.state.custom_state or {}
        execution_context = ""
        if custom_state.get("last_agent_id"):
            execution_context = (
                f"\nPrevious Execution Context:\n"
                f"  Last agent: {custom_state.get('last_agent_id')}\n"
                f"  Success: {custom_state.get('last_result_success')}\n"
                f"  Error: {custom_state.get('last_result_error')}\n"
                f"  Message: {custom_state.get('last_result_message')}\n"
                f"  Files changed: {custom_state.get('last_changed_files')}\n"
            )

        prompt = (
            f"{supervisor_def.prompt}\n\n"
            "Available Agents:\n"
            f"{json.dumps(available_agents, indent=2, ensure_ascii=False)}\n\n"
            "Response Instructions:\n"
            "You must manage the main task by creating and updating sub-tasks in the Blackboard.\n"
            "Respond ONLY with a JSON object in the following format (no other text):\n"
            "{\n"
            '  "sub_tasks": [\n'
            '    {"id": "task1", "description": "...", "status": "pending|in_progress|completed|failed", "assigned_to": "agent_id"}\n'
            "  ],\n"
            '  "next_agent": "agent_id_or_null",\n'
            '  "instruction": "What the next agent should do",\n'
            '  "type": "action|final",\n'
            '  "message": "Final message if type is final"\n'
            "}\n\n"
            f"Main Task: {task}\n"
            f"Current Blackboard State:\n{blackboard.to_summary()}"
            f"{execution_context}"
        )

        return await self._call_llm_json(
            prompt,
            task_type="supervisor",
            profile_name=supervisor_def.model_profile if supervisor_def else None,
        )

    async def run_planner_coder_reviewer(
        self, task: str | list[dict[str, Any]], max_iterations: int = 3
    ) -> ExecutionResult:
        task_str = json.dumps(task) if isinstance(task, list) else task
        blackboard = Blackboard(task_str)
        last_result: ExecutionResult | None = None

        for i in range(max_iterations):
            logger.info("Multi-agent iteration %d/%d", i + 1, max_iterations)

            bb_summary = blackboard.to_summary()

            plan = await self._call_planner(task_str, bb_summary)
            if not plan:
                logger.warning(
                    "Planner returned empty plan; allowing coder to proceed without plan"
                )
                plan = [{"type": "plan", "message": "Continue with implementation"}]

            logger.info("Planner generated %d actions", len(plan))
            blackboard.set_plan(plan)
            blackboard.add_message(
                "Planner",
                "Orchestrator",
                f"Generated plan with {len(plan)} actions",
                {"plan": plan},
            )

            result = await self.coding_loop.run(task_str, action_plan=plan)
            last_result = result

            changed_files = result.metrics.get("changed_files", []) if result.metrics else []
            blackboard.record_changes(changed_files)
            blackboard.add_message(
                "Coder",
                "Orchestrator",
                f"Execution finished. Success: {result.success}",
                {"changed_files": changed_files},
            )

            if not result.success:
                logger.warning("Coder failed: %s", result.error)
                result.events.append(
                    {
                        "event": "multi_agent.dialog",
                        "messages": [m.model_dump(mode="json") for m in blackboard.state.messages],
                    }
                )
                return result

            review = await self._call_reviewer(task_str, plan, result, blackboard)
            if review and review.get("status") == "approved":
                logger.info("Reviewer approved the changes")
                blackboard.add_message("Reviewer", "Orchestrator", "Approved changes.")
                result.events.append(
                    {
                        "event": "multi_agent.dialog",
                        "messages": [m.model_dump(mode="json") for m in blackboard.state.messages],
                    }
                )
                return result

            feedback_msg = "No feedback provided"
            if review:
                feedback_msg = review.get("feedback", "No feedback provided")
                logger.info("Reviewer requested adjustments: %s", feedback_msg)
            else:
                logger.warning("Reviewer returned no valid response; retrying iteration")

            blackboard.add_reviewer_feedback(feedback_msg)
            blackboard.add_message("Reviewer", "Planner", f"Rejected: {feedback_msg}")

        if last_result is None:
            raise RuntimeError("Multi-agent loop failed to produce a result")

        last_result.events.append(
            {
                "event": "multi_agent.dialog",
                "messages": [m.model_dump(mode="json") for m in blackboard.state.messages],
            }
        )
        return last_result

    async def _call_planner(self, task: str, blackboard_summary: str) -> list[dict[str, Any]]:
        prompt = (
            "You are a Planner Agent. Given the task and current work memory below, "
            "generate a list of actions to solve it.\n"
            "Respond ONLY with a JSON list of actions, where each action has a 'type' key.\n"
            "Format example:\n"
            "[\n"
            '  {"type": "write_file", "path": "OUTPUT.md", "content": "Hello World"},\n'
            '  {"type": "final", "message": "Task completed successfully"}\n'
            "]\n\n"
            "Available action types and their arguments:\n"
            "- read_file (keys: type, path)\n"
            "- write_file (keys: type, path, content)\n"
            "- apply_patch (keys: type, diff)\n"
            "- run_shell (keys: type, command)\n"
            "- run_tests (keys: type)\n"
            "- final (keys: type, message)\n\n"
            f"Task:\n{task}\n\n"
            f"Current State:\n{blackboard_summary}"
        )

        result = await self._call_llm_json(prompt, task_type="planner")
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            if "actions" in result:
                actions = result["actions"]
                return actions if isinstance(actions, list) else [result]
            return [result]

        logger.warning("Planner returned invalid format; using empty plan")
        return []

    async def _call_reviewer(
        self, task: str, plan: list[dict[str, Any]], result: ExecutionResult, blackboard: Blackboard
    ) -> dict[str, Any] | None:
        prompt = (
            "You are a Reviewer Agent. Review the execution result of the "
            "following task, current plan and blackboard state.\n"
            "Decide if the task is completed correctly.\n"
            "Respond ONLY with a JSON object: "
            '{"status": "approved|rejected", "feedback": "..."}\n\n'
            f"Task: {task}\n"
            f"Plan: {json.dumps(plan)}\n"
            f"Result Success: {result.success}\n"
            f"Message: {result.message}\n"
            f"Modified Files: {result.metrics.get('changed_files') if result.metrics else None}\n\n"
            f"Current Blackboard State:\n{blackboard.to_summary()}"
        )

        result_data = await self._call_llm_json(prompt, task_type="reviewer")
        if isinstance(result_data, dict) and "status" in result_data:
            return result_data

        logger.warning("Reviewer returned invalid JSON or missing status field")
        return None
