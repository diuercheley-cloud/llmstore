from typing import Any, Dict, List, Union
from app.utils.token_estimator import estimate_tokens_from_text, estimate_prompt_tokens

class FallbackTokenCounter:
    """Fallback token counter using character/word heuristic rules."""

    def count_prompt_tokens(self, prompt: Union[str, List[Dict[str, Any]]], model: str) -> int:
        if isinstance(prompt, str):
            return estimate_tokens_from_text(prompt)
        return estimate_prompt_tokens(messages=prompt)

    def count_completion_tokens(self, completion: str, model: str) -> int:
        return estimate_tokens_from_text(completion)
