import inspect
import logging
from collections.abc import Callable, Coroutine
from typing import Any

from .tokenizer import TokenCounter

logger = logging.getLogger(__name__)

class ContextManager:
    """
    Manages the context window for LLM calls.
    Handles pruning, summarization, and preservation of critical messages.
    """
    def __init__(
        self,
        max_context_tokens: int = 4096,
        reserved_output_tokens: int = 1024,
        token_counter: TokenCounter | None = None,
        summarize_func: Callable[[str], str | Coroutine[Any, Any, str]] | None = None
    ):
        self.max_context_tokens = max_context_tokens
        self.reserved_output_tokens = reserved_output_tokens
        self.token_counter = token_counter or TokenCounter()
        self.summarize_func = summarize_func

        # Metrics
        self.tokens_before = 0
        self.tokens_after = 0
        self.pruned_messages = 0
        self.summarized_count = 0

    async def manage_context(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Prunes or summarizes messages to fit within the context window.
        """
        if not messages:
            return []

        self.tokens_before = self.token_counter.count_messages(messages)
        allowed_tokens = self.max_context_tokens - self.reserved_output_tokens

        if self.tokens_before <= allowed_tokens:
            self.tokens_after = self.tokens_before
            return messages

        logger.info(
            f"Context window exceeded ({self.tokens_before} > {allowed_tokens}). "
            "Applying management strategies..."
        )

        # 1. Identify critical messages that SHOULD NOT be pruned easily
        # - System messages (policy, instructions)
        # - First user message (the original task)
        # - Latest few messages (immediate context)

        system_indices = [i for i, m in enumerate(messages) if m.get("role") == "system"]

        first_user_index = -1
        for i, m in enumerate(messages):
            if m.get("role") == "user":
                first_user_index = i
                break

        latest_count = 5
        latest_indices = list(range(max(0, len(messages) - latest_count), len(messages)))

        critical_indices = set(system_indices)
        if first_user_index != -1:
            critical_indices.add(first_user_index)
        critical_indices.update(latest_indices)

        # 2. Strategy A: Selective pruning/summarization of tool results
        processed_messages = []
        for i, m in enumerate(messages):
            if i in critical_indices:
                processed_messages.append(m)
                continue

            content = str(m.get("content", ""))
            # If it's a large tool result, try to truncate or summarize
            if ("[Tool Result:" in content or "Output:" in content) and len(content) > 1000:
                self.summarized_count += 1
                if self.summarize_func:
                    if inspect.iscoroutinefunction(self.summarize_func):
                        new_content = await self.summarize_func(content)
                    else:
                        new_content = self.summarize_func(content)
                else:
                    # Basic truncation with marker
                    new_content = content[:800] + "\n... [TRUNCATED BY CONTEXT MANAGER] ..."

                processed_messages.append({**m, "content": new_content})
            else:
                processed_messages.append(m)

        # Check if we are now under budget
        current_tokens = self.token_counter.count_messages(processed_messages)
        if current_tokens <= allowed_tokens:
            self.tokens_after = current_tokens
            return processed_messages

        # 3. Strategy B: Sliding window (dropping oldest non-critical messages)
        # We'll keep all critical messages and then as many as possible from the rest,
        # starting from the most recent.

        final_messages_indices = sorted(list(critical_indices))
        # Recalculate budget for non-critical messages
        critical_msgs = [messages[i] for i in final_messages_indices]
        budget = allowed_tokens - self.token_counter.count_messages(critical_msgs)

        if budget < 0:
            # Even critical messages are too many!
            # We must prune even some critical messages (except system and first user)
            logger.warning("Critical messages exceed context window. Pruning latest context.")
            # Keep only system and first user
            absolute_minimum = set(system_indices)
            if first_user_index != -1:
                absolute_minimum.add(first_user_index)

            # Re-add latest from critical if they fit
            new_critical = sorted(list(absolute_minimum))
            min_msgs = [messages[i] for i in new_critical]
            budget = allowed_tokens - self.token_counter.count_messages(min_msgs)

            extra_to_add: list[int] = []
            for i in reversed(sorted(list(critical_indices - absolute_minimum))):
                m_tokens = self.token_counter.count_tokens(str(messages[i].get("content", ""))) + 4
                if budget >= m_tokens:
                    extra_to_add.insert(0, i)
                    budget -= m_tokens
                else:
                    break
            final_messages_indices = sorted(new_critical + extra_to_add)
        else:
            # Add non-critical messages from the end until budget is full
            non_critical_indices = [
                i for i in range(len(messages)) if i not in critical_indices
            ]

            to_add: list[int] = []
            for i in reversed(non_critical_indices):
                content = str(processed_messages[i].get("content", ""))
                m_tokens = self.token_counter.count_tokens(content) + 4
                if budget >= m_tokens:
                    to_add.insert(0, i)
                    budget -= m_tokens
                else:
                    self.pruned_messages += 1

            final_messages_indices = sorted(list(critical_indices) + to_add)

        final_messages = [processed_messages[i] for i in final_messages_indices]
        self.tokens_after = self.token_counter.count_messages(final_messages)

        logger.info(
            f"Context managed: {self.tokens_before} -> {self.tokens_after} tokens. "
            f"Pruned {self.pruned_messages} messages, Summarized {self.summarized_count}."
        )
        return final_messages

    def get_metrics(self) -> dict[str, Any]:
        return {
            "context_tokens_before": self.tokens_before,
            "context_tokens_after": self.tokens_after,
            "context_pruned_messages": self.pruned_messages,
            "context_summarized": self.summarized_count,
        }
