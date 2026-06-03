import logging
from typing import Any

from .prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)


class OpenAICodeAgent:
    """
    Coding agent that uses PromptBuilder to include policy context.
    """

    def __init__(self, agent_id: str, policy_summary: str = ""):
        self.agent_id = agent_id
        self.prompt_builder = PromptBuilder(policy_summary=policy_summary)

    def get_initial_messages(self, task: str, context: str = "") -> list[dict[str, Any]]:
        system_prompt = self.prompt_builder.build_system_prompt()
        user_prompt = self.prompt_builder.build_task_prompt(task, context)

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]


class CodeAgent(OpenAICodeAgent):
    """
    Coding Agent representation that acts as a configuration and state helper
    for real providers and client executions.
    """

    def __init__(
        self,
        agent_id: str,
        provider: str = "openai-compatible",
        config: dict[str, Any] | None = None,
        policy_summary: str = "",
    ):
        super().__init__(agent_id=agent_id, policy_summary=policy_summary)
        self.provider = provider
        self.config = config or {}

    def validate_config(self) -> None:
        """
        Validates configuration values for the associated provider.
        """
        if not self.agent_id:
            raise ValueError("agent_id is required")

        if self.provider == "openai-compatible":
            if not self.config.get("base_url"):
                raise ValueError(f"base_url is required for provider {self.provider}")
            if not self.config.get("model"):
                raise ValueError(f"model is required for provider {self.provider}")
        elif self.provider == "local-openai-compatible":
            if not self.config.get("base_url"):
                raise ValueError(f"base_url is required for provider {self.provider}")
        elif self.provider == "control-plane":
            if not self.config.get("base_url"):
                raise ValueError("base_url is required for provider control-plane")
        elif self.provider == "stub":
            # Stub config validation has no required fields
            pass
