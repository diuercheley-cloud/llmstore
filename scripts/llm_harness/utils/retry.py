import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

T = TypeVar("T")

logger = logging.getLogger("llm_harness.utils.retry")


async def async_retry(
    fn: Callable[..., Awaitable[T]],
    *args: Any,
    max_retries: int = 3,
    base_delay: float = 1.0,
    retryable_errors: tuple[type[Exception], ...] | None = None,
    non_retryable_errors: tuple[type[Exception], ...] | None = None,
    **kwargs: Any,
) -> T:
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return await fn(*args, **kwargs)
        except non_retryable_errors or () as e:
            raise e
        except retryable_errors or (Exception,) as e:
            last_exc = e
            if attempt < max_retries:
                delay = base_delay * (2**attempt)
                logger.warning(
                    "Retry %d/%d for %s after %.1fs: %s",
                    attempt + 1,
                    max_retries,
                    fn.__name__,
                    delay,
                    e,
                )
                await asyncio.sleep(delay)
    raise last_exc  # type: ignore[misc]
