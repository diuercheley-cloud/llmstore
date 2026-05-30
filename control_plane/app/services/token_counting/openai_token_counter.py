import importlib
import logging
from typing import Any, Dict, List, Union

logger = logging.getLogger(__name__)

def _load_tiktoken():
    try:
        return importlib.import_module("tiktoken")
    except ImportError:
        return None

class OpenAITokenCounter:
    """Token counter using tiktoken for OpenAI models (gpt-*)."""

    def __init__(self, fallback_counter=None, fallback_allowed: bool = True):
        self.fallback_counter = fallback_counter
        self.fallback_allowed = fallback_allowed
        self._tiktoken_cache = {}

    def _get_tiktoken_encoding(self, model: str):
        tiktoken = _load_tiktoken()
        if not tiktoken:
            raise ImportError("tiktoken package is not installed")

        if model not in self._tiktoken_cache:
            try:
                self._tiktoken_cache[model] = tiktoken.encoding_for_model(model)
            except KeyError:
                self._tiktoken_cache[model] = tiktoken.get_encoding("cl100k_base")
        return self._tiktoken_cache[model]

    def count_prompt_tokens(self, prompt: Union[str, List[Dict[str, Any]]], model: str) -> tuple[int, str, bool]:
        """
        Returns (token_count, tokenizer_used, fallback_used)
        """
        tiktoken = _load_tiktoken()
        if not tiktoken:
            if self.fallback_allowed and self.fallback_counter:
                return self.fallback_counter.count_prompt_tokens(prompt, model), "fallback", True
            raise ImportError("tiktoken is not available and fallback is disabled")

        try:
            encoding = self._get_tiktoken_encoding(model)
            if isinstance(prompt, str):
                return len(encoding.encode(prompt)), "openai", False

            # Count chat messages
            num_tokens = 0
            for message in prompt:
                num_tokens += 4  # message overhead
                for key, value in message.items():
                    num_tokens += len(encoding.encode(str(value)))
                    if key == "name":
                        num_tokens += -1
            num_tokens += 2  # assistant reply prefix
            return num_tokens, "openai", False
        except Exception as e:
            logger.warning(f"OpenAI token counting failed: {e}")
            if self.fallback_allowed and self.fallback_counter:
                return self.fallback_counter.count_prompt_tokens(prompt, model), "fallback", True
            raise

    def count_completion_tokens(self, completion: str, model: str) -> tuple[int, str, bool]:
        tiktoken = _load_tiktoken()
        if not tiktoken:
            if self.fallback_allowed and self.fallback_counter:
                return self.fallback_counter.count_completion_tokens(completion, model), "fallback", True
            raise ImportError("tiktoken is not available and fallback is disabled")

        try:
            encoding = self._get_tiktoken_encoding(model)
            return len(encoding.encode(completion)), "openai", False
        except Exception as e:
            logger.warning(f"OpenAI token counting failed: {e}")
            if self.fallback_allowed and self.fallback_counter:
                return self.fallback_counter.count_completion_tokens(completion, model), "fallback", True
            raise
