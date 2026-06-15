# Owner: agent-platform
from enum import IntEnum


class SpanPriority(IntEnum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    DEBUG = 3


CRITICAL_SPAN_TYPES = frozenset(
    {
        "error",
        "policy_denial",
        "approval",
        "security",
    }
)

HIGH_SPAN_TYPES = frozenset(
    {
        "run_start",
        "run_end",
        "tool_call",
    }
)

NORMAL_SPAN_TYPES = frozenset(
    {
        "model_call",
        "memory_call",
    }
)

DEBUG_SPAN_TYPES = frozenset(
    {
        "token_usage",
        "debug",
        "llm_trace_debug",
    }
)


def classify_span_priority(span_type: str) -> SpanPriority:
    if span_type in CRITICAL_SPAN_TYPES:
        return SpanPriority.CRITICAL
    if span_type in HIGH_SPAN_TYPES:
        return SpanPriority.HIGH
    if span_type in NORMAL_SPAN_TYPES:
        return SpanPriority.NORMAL
    if span_type in DEBUG_SPAN_TYPES:
        return SpanPriority.DEBUG
    return SpanPriority.NORMAL


def can_drop(priority: SpanPriority) -> bool:
    return priority >= SpanPriority.NORMAL


def should_never_drop(priority: SpanPriority) -> bool:
    return priority == SpanPriority.CRITICAL
