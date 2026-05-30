import importlib
import logging
from typing import Any, Dict, List, Union

logger = logging.getLogger(__name__)

def _load_hf_tokenizer_cls():
    try:
        return importlib.import_module("tokenizers").Tokenizer
    except (ImportError, AttributeError):
        return None

class LlamaTokenCounter:
    """Token counter for LLaMA models using a SentencePiece/HuggingFace tokenizer if available."""

    def __init__(self, fallback_counter=None, fallback_allowed: bool = True, tokenizer_model_path: str | None = None):
        self.fallback_counter = fallback_counter
        self.fallback_allowed = fallback_allowed
        self._hf_tokenizer = None
        if tokenizer_model_path:
            tokenizer_cls = _load_hf_tokenizer_cls()
            if tokenizer_cls:
                try:
                    self._hf_tokenizer = tokenizer_cls.from_file(tokenizer_model_path)
                except Exception as e:
                    logger.warning(f"Failed to load HF tokenizer for LLaMA: {e}")

    def count_prompt_tokens(self, prompt: Union[str, List[Dict[str, Any]]], model: str) -> tuple[int, str, bool]:
        if self._hf_tokenizer:
            try:
                if isinstance(prompt, str):
                    tokens = self._hf_tokenizer.encode(prompt)
                    return len(tokens.ids), "llama", False
                else:
                    full_text = ""
                    for m in prompt:
                        full_text += f"{m.get('role', '')} {m.get('content', '')}\n"
                    tokens = self._hf_tokenizer.encode(full_text)
                    return len(tokens.ids), "llama", False
            except Exception as e:
                logger.warning(f"Llama HF token counting failed: {e}")

        if self.fallback_allowed and self.fallback_counter:
            return self.fallback_counter.count_prompt_tokens(prompt, model), "fallback", True
        raise RuntimeError("LLaMA tokenizer not available and fallback is disabled")

    def count_completion_tokens(self, completion: str, model: str) -> tuple[int, str, bool]:
        if self._hf_tokenizer:
            try:
                tokens = self._hf_tokenizer.encode(completion)
                return len(tokens.ids), "llama", False
            except Exception as e:
                logger.warning(f"Llama HF token counting failed: {e}")

        if self.fallback_allowed and self.fallback_counter:
            return self.fallback_counter.count_completion_tokens(completion, model), "fallback", True
        raise RuntimeError("LLaMA tokenizer not available and fallback is disabled")
