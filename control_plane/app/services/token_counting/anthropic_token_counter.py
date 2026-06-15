import importlib
import logging
from typing import Any, Union

logger = logging.getLogger(__name__)


def _load_tiktoken():
    try:
        return importlib.import_module("tiktoken")
    except ImportError:
        return None


class AnthropicTokenCounter:
    """Token counter for Anthropic Claude models."""

    def __init__(self, fallback_counter=None, fallback_allowed: bool = True):
        self.fallback_counter = fallback_counter
        self.fallback_allowed = fallback_allowed

    def count_prompt_tokens(
        self, prompt: Union[str, list[dict[str, Any]]], model: str
    ) -> tuple[int, str, bool]:
        tiktoken = _load_tiktoken()
        if not tiktoken:
            if self.fallback_allowed and self.fallback_counter:
                return self.fallback_counter.count_prompt_tokens(prompt, model), "fallback", True
            raise ImportError("tiktoken is not available and fallback is disabled")

        try:
            encoding = tiktoken.get_encoding("cl100k_base")
            if isinstance(prompt, str):
                return len(encoding.encode(prompt)), "anthropic", False

            num_tokens = 0
            for message in prompt:
                num_tokens += 4
                for key, value in message.items():
                    num_tokens += len(encoding.encode(str(value)))
            return num_tokens, "anthropic", False
        except Exception as e:
            logger.warning(f"Anthropic token counting failed: {e}")
            if self.fallback_allowed and self.fallback_counter:
                return self.fallback_counter.count_prompt_tokens(prompt, model), "fallback", True
            raise

    def count_completion_tokens(self, completion: str, model: str) -> tuple[int, str, bool]:
        tiktoken = _load_tiktoken()
        if not tiktoken:
            if self.fallback_allowed and self.fallback_counter:
                return (
                    self.fallback_counter.count_completion_tokens(completion, model),
                    "fallback",
                    True,
                )
            raise ImportError("tiktoken is not available and fallback is disabled")

        try:
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(completion)), "anthropic", False
        except Exception as e:
            logger.warning(f"Anthropic token counting failed: {e}")
            if self.fallback_allowed and self.fallback_counter:
                return (
                    self.fallback_counter.count_completion_tokens(completion, model),
                    "fallback",
                    True,
                )
            raise
