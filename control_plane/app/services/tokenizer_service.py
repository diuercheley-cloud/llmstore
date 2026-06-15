import functools
import importlib
import logging
from typing import Union

from app.contracts.token_accounting import (
    TokenAccountingCapabilities,
    TokenAccountingContract,
    TokenCountResult,
)
from app.core.config import get_settings
from app.utils.token_estimator import estimate_prompt_tokens, estimate_tokens_from_text

logger = logging.getLogger(__name__)


def _load_tiktoken():
    try:
        return importlib.import_module("tiktoken")
    except ImportError:
        return None


def _load_hf_tokenizer_cls():
    try:
        return importlib.import_module("tokenizers").Tokenizer
    except (ImportError, AttributeError):
        return None


class TokenizerService(TokenAccountingContract):
    def __init__(self):
        self.settings = get_settings()
        self._tiktoken_cache = {}
        self._hf_tokenizer = None
        if self.settings.tokenizer_model_path:
            tokenizer_cls = _load_hf_tokenizer_cls()
            if not tokenizer_cls:
                logger.error("tokenizers library is not installed but TOKENIZER_MODEL_PATH is set")
            else:
                try:
                    self._hf_tokenizer = tokenizer_cls.from_file(self.settings.tokenizer_model_path)
                    logger.info(
                        f"Loaded HuggingFace tokenizer from {self.settings.tokenizer_model_path}"
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to load HF tokenizer from {self.settings.tokenizer_model_path}: {e}"
                    )

    def capabilities(self) -> TokenAccountingCapabilities:
        return TokenAccountingCapabilities(
            native_tiktoken=_load_tiktoken() is not None,
            hf_tokenizers=self._hf_tokenizer is not None,
        )

    def validate_contract(self) -> bool:
        return True

    def _get_tiktoken_encoding(self, model: str):
        tiktoken = _load_tiktoken()
        if not tiktoken:
            raise ImportError("tiktoken is not installed")
        if not self.settings.tokenizer_cache_enabled:
            try:
                return tiktoken.encoding_for_model(model)
            except KeyError:
                return tiktoken.get_encoding("cl100k_base")

        if model not in self._tiktoken_cache:
            try:
                self._tiktoken_cache[model] = tiktoken.encoding_for_model(model)
            except KeyError:
                self._tiktoken_cache[model] = tiktoken.get_encoding("cl100k_base")
        return self._tiktoken_cache[model]

    async def count_text_tokens(self, text: str, model: str | None = None) -> TokenCountResult:
        openai_like_model = bool(
            model
            and (
                model.startswith("gpt-") or "claude" in model.lower() or "deepseek" in model.lower()
            )
        )
        real_counter_available = not openai_like_model or _load_tiktoken() is not None
        if self.settings.token_counting_real_enabled and real_counter_available:
            from app.services.token_counting.token_counter import TokenCounter

            tc = TokenCounter()
            res = tc.count_tokens(prompt=text, completion="", model=model or "gpt-3.5-turbo")
            if self.settings.tokenizer_strict and res.fallback_used:
                raise RuntimeError(
                    f"Strict tokenization enabled but real tokenizer failed for model {model}"
                )
            return TokenCountResult(
                input_tokens=res.prompt_tokens,
                output_tokens=res.completion_tokens,
                total_tokens=res.total_tokens,
                method=res.tokenizer_used,
                model=model,
                is_estimated=res.fallback_used,
            )

        if not text:
            return TokenCountResult(
                input_tokens=0, total_tokens=0, method="estimated", is_estimated=True
            )

        # HF Tokenizer priority if configured
        if self._hf_tokenizer:
            try:
                tokens = self._hf_tokenizer.encode(text)
                count = len(tokens.ids)
                return TokenCountResult(
                    input_tokens=count,
                    total_tokens=count,
                    method="hf_tokenizer",
                    model=model,
                    is_estimated=False,
                )
            except Exception as e:
                logger.warning(f"HF tokenizer failed: {e}")
                if self.settings.tokenizer_strict:
                    raise

        # Tiktoken for OpenAI-like models
        if openai_like_model:
            try:
                encoding = self._get_tiktoken_encoding(model)
                count = len(encoding.encode(text))
                return TokenCountResult(
                    input_tokens=count,
                    total_tokens=count,
                    method="tiktoken",
                    model=model,
                    is_estimated=False,
                )
            except Exception as e:
                logger.warning(f"Tiktoken failed for model {model}: {e}")
                if self.settings.tokenizer_strict:
                    raise

        # Fallback to estimation
        if self.settings.tokenizer_strict:
            raise RuntimeError(
                f"Strict tokenization enabled but no real tokenizer found for model {model}"
            )

        count = estimate_tokens_from_text(text)
        return TokenCountResult(
            input_tokens=count,
            total_tokens=count,
            method="estimated",
            model=model,
            is_estimated=True,
        )

    async def count_chat_tokens(
        self, messages: list[dict], model: str | None = None
    ) -> TokenCountResult:
        if self.settings.token_counting_real_enabled:
            from app.services.token_counting.token_counter import TokenCounter

            tc = TokenCounter()
            res = tc.count_tokens(prompt=messages, completion="", model=model or "gpt-3.5-turbo")
            if self.settings.tokenizer_strict and res.fallback_used:
                raise RuntimeError(
                    f"Strict tokenization enabled but real tokenizer failed for chat model {model}"
                )
            return TokenCountResult(
                input_tokens=res.prompt_tokens,
                output_tokens=res.completion_tokens,
                total_tokens=res.total_tokens,
                method=res.tokenizer_used,
                model=model,
                is_estimated=res.fallback_used,
            )

        if not messages:
            return TokenCountResult(
                input_tokens=0, total_tokens=0, method="estimated", is_estimated=True
            )

        # Try to use tiktoken for chat if model is known
        if model and model.startswith("gpt-"):
            try:
                encoding = self._get_tiktoken_encoding(model)
                num_tokens = 0
                for message in messages:
                    num_tokens += (
                        4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
                    )
                    for key, value in message.items():
                        num_tokens += len(encoding.encode(str(value)))
                        if key == "name":  # if there's a name, the role is omitted
                            num_tokens += -1  # role is always 1 token
                num_tokens += 2  # every reply is primed with <im_start>assistant
                return TokenCountResult(
                    input_tokens=num_tokens,
                    total_tokens=num_tokens,
                    method="tiktoken",
                    model=model,
                    is_estimated=False,
                )
            except Exception as e:
                logger.warning(f"Tiktoken chat counting failed: {e}")
                if self.settings.tokenizer_strict:
                    raise

        # HF Tokenizer for chat (very basic implementation, just concatenate contents)
        if self._hf_tokenizer:
            try:
                full_text = ""
                for m in messages:
                    full_text += f"{m.get('role', '')} {m.get('content', '')}\n"
                tokens = self._hf_tokenizer.encode(full_text)
                count = len(tokens.ids)
                return TokenCountResult(
                    input_tokens=count,
                    total_tokens=count,
                    method="hf_tokenizer",
                    model=model,
                    is_estimated=False,
                )
            except Exception as e:
                logger.warning(f"HF tokenizer chat failed: {e}")
                if self.settings.tokenizer_strict:
                    raise

        # Fallback
        if self.settings.tokenizer_strict:
            raise RuntimeError(
                f"Strict tokenization enabled but no real tokenizer found for chat model {model}"
            )

        count = estimate_prompt_tokens(messages=messages)
        return TokenCountResult(
            input_tokens=count,
            total_tokens=count,
            method="estimated",
            model=model,
            is_estimated=True,
        )

    async def count_embedding_tokens(
        self, input: Union[str, list[str]], model: str | None = None
    ) -> TokenCountResult:
        if self.settings.token_counting_real_enabled:
            if isinstance(input, str):
                texts = [input]
            else:
                texts = input
            total_count = 0
            method = "estimated"
            is_estimated = True
            from app.services.token_counting.token_counter import TokenCounter

            tc = TokenCounter()
            for text in texts:
                res = tc.count_tokens(
                    prompt=text, completion="", model=model or "text-embedding-3-small"
                )
                if self.settings.tokenizer_strict and res.fallback_used:
                    raise RuntimeError(
                        f"Strict tokenization enabled but real tokenizer failed for embedding model {model}"
                    )
                total_count += res.prompt_tokens
                method = res.tokenizer_used
                is_estimated = res.fallback_used
            return TokenCountResult(
                input_tokens=total_count,
                total_tokens=total_count,
                method=method,
                model=model,
                is_estimated=is_estimated,
            )

        if isinstance(input, str):
            texts = [input]
        else:
            texts = input

        total_count = 0
        method = "estimated"
        is_estimated = True

        for text in texts:
            res = await self.count_text_tokens(text, model)
            total_count += res.input_tokens
            method = res.method
            is_estimated = res.is_estimated

        return TokenCountResult(
            input_tokens=total_count,
            total_tokens=total_count,
            method=method,
            model=model,
            is_estimated=is_estimated,
        )


@functools.lru_cache
def get_tokenizer_service() -> TokenizerService:
    return TokenizerService()
