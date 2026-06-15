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
        rules_context: str = "",
        language_profile: Any = None,
        interaction_mode: str = "agentic",
        is_reasoning_model: bool = False,
    ):
        self.policy_summary = policy_summary
        self.memory_context = memory_context
        self.task_type = task_type
        self.few_shots = few_shots or []
        self.retrieved_context = retrieved_context
        self.eval_feedback = eval_feedback
        self.rules_context = rules_context
        self.language_profile = language_profile
        self.interaction_mode = interaction_mode
        self.is_reasoning_model = is_reasoning_model

    def build_system_prompt(self) -> str:
        if self.interaction_mode == "chat":
            prompt = f"You are an IDE assistant specialized in {self.task_type}.\n"
            prompt += (
                "Answer in normal prose, stay concise, use the provided context, "
                "and do not emit JSON actions unless the user explicitly asks for them.\n\n"
            )
        else:
            prompt = (
                f"You are a Senior Software Engineer AI Agent specialized in {self.task_type}.\n"
            )
            prompt += "Your goal is to solve the task autonomously and safely.\n\n"

        if self.is_reasoning_model:
            prompt += (
                "You have advanced reasoning capabilities. Use your chain-of-thought "
                "reasoning to thoroughly analyze the task before producing your answer. "
                "Separate your internal reasoning from your final answer. "
                "Your final answer must still be valid JSON following the action schema.\n\n"
            )

        if self.language_profile:
            lp = self.language_profile
            is_dict = isinstance(lp, dict)
            name = lp.get("name") if is_dict else getattr(lp, "name", None)
            exts = lp.get("extensions", []) if is_dict else getattr(lp, "extensions", [])
            test_cmd = lp.get("test_command") if is_dict else getattr(lp, "test_command", None)
            lint_cmd = lp.get("lint_command") if is_dict else getattr(lp, "lint_command", None)
            comment_style = (
                lp.get("comment_style") if is_dict else getattr(lp, "comment_style", None)
            )
            if name:
                prompt += f"## Language Profile: {name}\n"
                if exts:
                    prompt += f"- Extension(s): {', '.join(exts)}\n"
                if test_cmd:
                    prompt += f"- Suggested Test Command: {test_cmd}\n"
                if lint_cmd:
                    prompt += f"- Suggested Lint Command: {lint_cmd}\n"
                if comment_style:
                    prompt += f"- Comment Style: {comment_style}\n"
                prompt += "\n"

        if self.policy_summary:
            prompt += self.policy_summary + "\n"

        if self.rules_context:
            prompt += "## Custom AI Rules\n"
            prompt += self.rules_context + "\n\n"

        if self.retrieved_context:
            prompt += "## Retrieved Context\n"
            prompt += self.retrieved_context + "\n\n"

        if self.eval_feedback:
            prompt += "## Evaluation Feedback\n"
            prompt += self.eval_feedback + "\n\n"

        if self.memory_context:
            prompt += "## Persistent Memory\n"
            prompt += self.memory_context + "\n\n"

        if self.few_shots:
            prompt += "## Examples (Few-Shot)\n"
            for i, example in enumerate(self.few_shots):
                prompt += f"Example {i + 1}:\n{example}\n\n"

        prompt += "## Guidelines\n"
        if self.interaction_mode == "chat":
            prompt += "1. Prefer direct, useful answers over meta commentary.\n"
            prompt += "2. Respect workspace boundaries and never expose secrets.\n"
            prompt += "3. If context is insufficient, say what is missing.\n"
        else:
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
            normalized_task = []
            for b in task:
                if hasattr(b, "model_dump"):
                    normalized_task.append(b.model_dump())
                else:
                    normalized_task.append(b)
            task = normalized_task

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
