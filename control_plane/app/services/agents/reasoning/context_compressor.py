# Owner: agent-platform
import logging
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class ContextCompressor:
    """
    Compresses long conversation history to fit within model context limits.
    """

    def __init__(self, max_tokens_threshold: int = 8000):
        self.max_tokens_threshold = max_tokens_threshold
        self.settings = get_settings()

    async def compress_if_needed(self, history: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not self.settings.agent_context_compression_enabled:
            return history

        # Simplified token counting (in a real app, use a tokenizer)
        total_chars = sum(len(str(m)) for m in history)
        estimated_tokens = total_chars // 4

        if estimated_tokens < self.max_tokens_threshold:
            return history

        logger.info(f"Context compression triggered (est tokens: {estimated_tokens})")

        # Preservation logic: keep system, last N messages, and key events
        preserved = []
        # Keep system prompt
        preserved.extend([m for m in history if m.get("role") == "system"])

        # Keep latest 5 messages
        preserved.extend(history[-5:])

        # Summarize the middle part (mocked for now)
        summary = {
            "role": "system",
            "content": "[CONTEXT SUMMARY] Previous steps involved data gathering and initial analysis.",
        }

        return [preserved[0], summary] + preserved[1:]

    def redact_secrets(self, content: str) -> str:
        # Simple redaction logic
        import re

        patterns = [
            r"(api[_-]key[:\s=]+is\s+|api[_-]key[:\s=]+)[^\s'\"&,;]+",
            r"(secret[:\s=]+is\s+|secret[:\s=]+)[^\s'\"&,;]+",
            r"(password[:\s=]+is\s+|password[:\s=]+)[^\s'\"&,;]+",
            r"(token[:\s=]+is\s+|token[:\s=]+)[^\s'\"&,;]+",
        ]
        for p in patterns:
            content = re.sub(p, r"\1[REDACTED]", content, flags=re.IGNORECASE)
        return content
