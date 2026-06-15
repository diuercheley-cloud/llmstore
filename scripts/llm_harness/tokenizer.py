import logging
from typing import Any

logger = logging.getLogger(__name__)


class TokenCounter:
    """
    Counts tokens for different providers and models.
    Supports tiktoken if installed, otherwise falls back to character-based approximation.
    """

    def __init__(self, method: str = "auto"):
        self.method = method
        self._tiktoken_encoding = None

        if method in ("auto", "tiktoken"):
            try:
                import tiktoken

                self._tiktoken_encoding = tiktoken.get_encoding("cl100k_base")
                self.method = "tiktoken"
                logger.debug("Using tiktoken for token counting")
            except ImportError:
                if method == "tiktoken":
                    logger.warning("tiktoken requested but not found, falling back to approx")
                self.method = "approx"

    def count_tokens(self, text: str) -> int:
        if not text:
            return 0

        if self.method == "tiktoken" and self._tiktoken_encoding:
            try:
                return len(self._tiktoken_encoding.encode(text))
            except Exception as e:
                logger.error(f"tiktoken encoding failed: {e}, falling back to approx")
                return self._approx_tokens(text)

        return self._approx_tokens(text)

    def _approx_tokens(self, text: str) -> int:
        # Standard heuristic: 1 token ~= 4 characters for English text
        # Adding +1 to avoid 0 for very short strings
        return (len(text) // 4) + 1

    def count_messages(self, messages: list[dict[str, Any]]) -> int:
        """
        Approximate token count for a list of chat messages.
        """
        tokens = 0
        for message in messages:
            tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
            for _key, value in message.items():
                tokens += self.count_tokens(str(value))
        tokens += 2  # every reply is primed with <im_start>assistant
        return tokens

    def estimate_budget(
        self, messages: list[dict[str, Any]], max_tokens: int, reserved_output: int = 1024
    ) -> bool:
        """
        Check if the messages fit within the max_tokens budget,
        leaving room for reserved_output tokens.
        """
        current = self.count_messages(messages)
        return (current + reserved_output) <= max_tokens
