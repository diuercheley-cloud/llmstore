from typing import Any, Union

from app.core.config import get_settings
from app.services.token_counting.anthropic_token_counter import AnthropicTokenCounter
from app.services.token_counting.fallback_token_counter import FallbackTokenCounter
from app.services.token_counting.llama_token_counter import LlamaTokenCounter
from app.services.token_counting.openai_token_counter import OpenAITokenCounter


class TokenCountingResult:
    def __init__(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        tokenizer_used: str,
        fallback_used: bool,
    ):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens
        self.tokenizer_used = tokenizer_used
        self.fallback_used = fallback_used

    def to_dict(self) -> dict[str, Any]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "tokenizer_used": self.tokenizer_used,
            "fallback_used": self.fallback_used,
        }


class TokenCounter:
    """Main coordinator to route token counting to specific model/provider tokenizer implementations."""

    def __init__(self):
        settings = get_settings()
        self.real_enabled = getattr(settings, "token_counting_real_enabled", False)
        self.fallback_allowed = getattr(settings, "token_counting_fallback_allowed", True)

        self.fallback_counter = FallbackTokenCounter()
        self.openai_counter = OpenAITokenCounter(
            fallback_counter=self.fallback_counter, fallback_allowed=self.fallback_allowed
        )
        self.anthropic_counter = AnthropicTokenCounter(
            fallback_counter=self.fallback_counter, fallback_allowed=self.fallback_allowed
        )
        self.llama_counter = LlamaTokenCounter(
            fallback_counter=self.fallback_counter,
            fallback_allowed=self.fallback_allowed,
            tokenizer_model_path=getattr(settings, "tokenizer_model_path", None),
        )

    def _get_counter_for_model(self, model: str, provider: str | None = None):
        m_lower = model.lower() if model else ""
        p_lower = provider.lower() if provider else ""

        if "gpt-" in m_lower or "openai" in p_lower or "text-embedding" in m_lower:
            return self.openai_counter
        elif "claude" in m_lower or "anthropic" in p_lower:
            return self.anthropic_counter
        elif "llama" in m_lower or "llama" in p_lower:
            return self.llama_counter
        else:
            return (
                self.openai_counter
            )  # Default to OpenAI counter (supports cl100k_base or fallback)

    def count_tokens(
        self,
        prompt: Union[str, list[dict[str, Any]]],
        completion: str | None,
        model: str,
        provider: str | None = None,
    ) -> TokenCountingResult:
        """
        Counts prompt and completion tokens.
        If real token counting is disabled or fallback is forced/required, it will use fallback.
        """
        if not self.real_enabled:
            if not self.fallback_allowed:
                raise RuntimeError("Real token counting is disabled and fallback is not allowed")

            p_tokens = self.fallback_counter.count_prompt_tokens(prompt, model)
            c_tokens = self.fallback_counter.count_completion_tokens(completion or "", model)
            return TokenCountingResult(
                prompt_tokens=p_tokens,
                completion_tokens=c_tokens,
                total_tokens=p_tokens + c_tokens,
                tokenizer_used="fallback",
                fallback_used=True,
            )

        counter = self._get_counter_for_model(model, provider)

        # Count prompt
        p_tokens, p_method, p_fallback = counter.count_prompt_tokens(prompt, model)

        # Count completion
        c_tokens, c_method, c_fallback = counter.count_completion_tokens(completion or "", model)

        # Combine results
        tokenizer_used = p_method if p_method == c_method else f"{p_method}/{c_method}"
        fallback_used = p_fallback or c_fallback

        return TokenCountingResult(
            prompt_tokens=p_tokens,
            completion_tokens=c_tokens,
            total_tokens=p_tokens + c_tokens,
            tokenizer_used=tokenizer_used,
            fallback_used=fallback_used,
        )
