# scripts/llm_harness/prompt_builder.py
from typing import Any


class PromptBuilder:
    """
    Builds rich prompts for coding agents, including policy context.
    """

    def __init__(
        self,
        policy_summary: str = "",
        memory_context: str = "",
        task_type: str = "general",
        few_shots: list[str] | None = None,
        retrieved_context: str = "",
        eval_feedback: str = "",
    ):
        self.policy_summary = policy_summary
        self.memory_context = memory_context
        self.task_type = task_type
        self.few_shots = few_shots or []
        self.retrieved_context = retrieved_context
        self.eval_feedback = eval_feedback

    def build_system_prompt(self) -> str:
        prompt = f"You are a Senior Software Engineer AI Agent specialized in {self.task_type}.\n"
        prompt += "Your goal is to solve the task autonomously and safely.\n\n"

        if self.policy_summary:
            prompt += self.policy_summary + "\n"

        if self.eval_feedback:
            prompt += "## Evaluation Feedback\n"
            prompt += self.eval_feedback + "\n\n"

        if self.memory_context:
            prompt += "## Persistent Memory\n"
            prompt += self.memory_context + "\n\n"

        if self.few_shots:
            prompt += "## Examples (Few-Shot)\n"
            for i, example in enumerate(self.few_shots):
                prompt += f"Example {i+1}:\n{example}\n\n"

        prompt += "## Guidelines\n"
        prompt += "1. Always produce valid JSON for actions.\n"
        prompt += "2. Prefer using 'apply_patch' or 'replace_content' for code changes.\n"
        prompt += "3. If an action is denied by policy, choose a safe alternative.\n"
        prompt += "4. Do not attempt to use 'sudo' or access forbidden files like '.env'.\n"
        prompt += (
            "5. Use this schema exactly: "
            '{"type":"plan|read_file|apply_patch|run_shell|run_tests|final",'
            '"reason":"...", "payload":{}}.\n'
        )

        return prompt

    def build_task_prompt(self, task: Any, context: str = "") -> Any:
        if isinstance(task, list):
            text_blocks = [b for b in task if b.get("type") == "text"]
            if text_blocks:
                orig_text = text_blocks[0].get("text", "")
                formatted_text = f"### Task\n{orig_text}\n\n"
                ctx = context or self.retrieved_context
                if ctx:
                    formatted_text += f"### Context\n{ctx}\n\n"
                formatted_text += "Respond only with the next action as a JSON object."
                
                new_task = []
                for b in task:
                    if b.get("type") == "text":
                        new_task.append({"type": "text", "text": formatted_text})
                    else:
                        new_task.append(b)
                return new_task
            else:
                formatted_text = "### Task\n\n"
                ctx = context or self.retrieved_context
                if ctx:
                    formatted_text += f"### Context\n{ctx}\n\n"
                formatted_text += "Respond only with the next action as a JSON object."
                return [{"type": "text", "text": formatted_text}] + task
        else:
            prompt = f"### Task\n{task}\n\n"
            ctx = context or self.retrieved_context
            if ctx:
                prompt += f"### Context\n{ctx}\n\n"
            prompt += "Respond only with the next action as a JSON object."
            return prompt

