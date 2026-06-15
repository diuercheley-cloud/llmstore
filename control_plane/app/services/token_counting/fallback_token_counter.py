from typing import Any, Union

from app.utils.token_estimator import estimate_prompt_tokens, estimate_tokens_from_text


class FallbackTokenCounter:
    """Fallback token counter using character/word heuristic rules."""

    def count_prompt_tokens(self, prompt: Union[str, list[dict[str, Any]]], model: str) -> int:
        if isinstance(prompt, str):
            return estimate_tokens_from_text(prompt)
        return estimate_prompt_tokens(messages=prompt)

    def count_completion_tokens(self, completion: str, model: str) -> int:
        return estimate_tokens_from_text(completion)
