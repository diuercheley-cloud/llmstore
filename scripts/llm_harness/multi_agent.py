import json
import logging
from typing import Any

from .coding_loop import CodingLoop
from .models import ExecutionResult

logger = logging.getLogger(__name__)

class MultiAgentOrchestrator:
    def __init__(self, coding_loop: CodingLoop):
        self.coding_loop = coding_loop
        self.agent_client = coding_loop.agent_client

    async def run_planner_coder_reviewer(
        self, task: str | list[dict[str, Any]], max_iterations: int = 3
    ) -> ExecutionResult:
        current_task = task
        last_result: ExecutionResult | None = None

        for i in range(max_iterations):
            logger.info(f"Multi-agent iteration {i+1}/{max_iterations}")

            # 1. Planner
            plan = await self._call_planner(current_task)
            logger.info(f"Planner generated {len(plan)} actions")

            # 2. Coder
            result = await self.coding_loop.run(current_task, action_plan=plan)
            last_result = result

            if not result.success:
                logger.warning(f"Coder failed: {result.error}")
                return result

            # 3. Reviewer
            review = await self._call_reviewer(current_task, plan, result)
            if review.get("status") == "approved":
                logger.info("Reviewer approved the changes")
                return result

            logger.info(f"Reviewer requested adjustments: {review.get('feedback')}")
            feedback_msg = review.get('feedback')
            current_task = f"{task}\n\nReviewer feedback from previous attempt:\n{feedback_msg}"

        if last_result is None:
             raise RuntimeError("Multi-agent loop failed to produce a result")

        return last_result

    async def _call_planner(self, task: str | list[dict[str, Any]]) -> list[dict[str, Any]]:
        prompt = (
            "You are a Planner Agent. Given the task below, "
            "generate a list of actions to solve it.\n"
            "Respond ONLY with a JSON list of actions.\n"
            "Action types: read_file, apply_patch, run_shell, run_tests, final.\n\n"
            f"Task: {task}"
        )
        messages = [{"role": "user", "content": prompt}]
        response = await self.agent_client.chat_completion(messages)
        content = response["choices"][0]["message"]["content"]

        # Simple extraction if it's wrapped in markdown
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        try:
            plan = json.loads(content)
            if isinstance(plan, dict) and "actions" in plan:
                plan = plan["actions"]
            if not isinstance(plan, list):
                plan = [plan]
            return plan
        except Exception as e:
            logger.error(f"Failed to parse planner response: {e}\nContent: {content}")
            # Fallback to empty plan (let Coder decide)
            return []

    async def _call_reviewer(
        self, task: str | list[dict[str, Any]], plan: list[dict[str, Any]], result: ExecutionResult
    ) -> dict[str, Any]:
        prompt = (
            "You are a Reviewer Agent. Review the execution result of the "
            "following task and plan.\n"
            "Decide if the task is completed correctly.\n"
            "Respond ONLY with a JSON object: "
            "{\"status\": \"approved|rejected\", \"feedback\": \"...\"}\n\n"
            f"Task: {task}\n"
            f"Plan: {json.dumps(plan)}\n"
            f"Result Success: {result.success}\n"
            f"Message: {result.message}\n"
            f"Modified Files: {result.metrics.get('changed_files')}\n"
        )
        messages = [{"role": "user", "content": prompt}]
        response = await self.agent_client.chat_completion(messages)
        content = response["choices"][0]["message"]["content"]

        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()

        try:
            review = json.loads(content)
            if not isinstance(review, dict) or "status" not in review:
                return {
                    "status": "review_failed",
                    "feedback": "Reviewer returned invalid JSON structure"
                }
            return review
        except Exception as e:
            logger.error(f"Failed to parse reviewer response: {e}\nContent: {content}")
            return {"status": "review_failed", "feedback": f"Reviewer returned invalid JSON: {e}"}
