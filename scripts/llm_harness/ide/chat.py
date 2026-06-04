from typing import Any, Optional

from ..context import ContextManager
from ..memory import LocalMemory
from ..policy import PolicyEngine
from ..prompt_builder import PromptBuilder
from ..tokenizer import TokenCounter


class IDEChatSession:
    def __init__(
        self,
        provider: Any,
        prompt_builder: PromptBuilder,
        policy_engine: PolicyEngine,
        memory: Optional[LocalMemory] = None,
        context_manager: Optional[ContextManager] = None,
        token_budget: int = 4096,
        rules_context: str = "",
    ):
        self.provider = provider
        self.prompt_builder = prompt_builder
        self.policy_engine = policy_engine
        self.memory = memory
        
        self.tokenizer = TokenCounter(method="auto")
        self.context_manager = context_manager or ContextManager(
            max_context_tokens=token_budget,
            reserved_output_tokens=1024,
            token_counter=self.tokenizer
        )
        self.rules_context = rules_context
        self.history: list[dict[str, Any]] = []

    async def send_message(self, message: Any, context_bundle: Optional[Any] = None) -> str:
        user_content: Any = None
        if isinstance(message, list):
            normalized_msg = []
            for b in message:
                if hasattr(b, "model_dump"):
                    normalized_msg.append(b.model_dump())
                else:
                    normalized_msg.append(b)
            user_content = normalized_msg
            if context_bundle and not context_bundle.is_empty():
                user_content = [{"type": "text", "text": context_bundle.to_text()}] + user_content
        else:
            user_content = message
            if context_bundle and not context_bundle.is_empty():
                user_content = f"{context_bundle.to_text()}\n\n{message}"

        self.history.append({"role": "user", "content": user_content})

        # Set the rules_context in PromptBuilder
        if self.rules_context:
            self.prompt_builder.rules_context = self.rules_context
            
        system_prompt = self.prompt_builder.build_system_prompt()

        messages = [{"role": "system", "content": system_prompt}] + self.history

        pruned_messages = await self.context_manager.manage_context(messages)

        # Sync history with pruned messages
        self.history = [m for m in pruned_messages if m.get("role") != "system"]

        response = await self.provider.chat_completion(pruned_messages)

        assistant_content = ""
        if response and "choices" in response and response["choices"]:
            msg = response["choices"][0].get("message", {})
            assistant_content = msg.get("content", "")
        
        self.history.append({"role": "assistant", "content": assistant_content})

        if self.memory:
            self.memory.record_run(
                task=f"Chat message: {message}",
                result={
                    "success": True,
                    "message": assistant_content,
                    "total_tokens": (
                        response.get("usage", {}).get("total_tokens", 0)
                        if response else 0
                    )
                }
            )

        return assistant_content
