import os
import uuid
from contextlib import contextmanager
from typing import Any

# Try to import OpenTelemetry, but don't fail if not present
try:
    from opentelemetry import trace
    from opentelemetry.trace import Status, StatusCode
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False


class Tracer:
    """
    Manages tracing for LLM harness.
    Supports internal IDs and optional OpenTelemetry.
    """
    def __init__(self, trace_id: str | None = None):
        self.trace_id = trace_id or str(uuid.uuid4())
        self.spans: dict[str, Any] = {}
        self.otel_tracer = None

        if OTEL_AVAILABLE and os.environ.get("LLM_HARNESS_ENABLE_OTEL") == "1":
            self.otel_tracer = trace.get_tracer("llm-harness")

    def _sanitize_attributes(self, attributes: dict[str, Any] | None) -> dict[str, Any] | None:
        if not attributes:
            return None
        from .sanitizer import Sanitizer
        sanitized = {}
        sensitive_keys = {"key", "token", "password", "secret", "auth", "credential"}
        for k, v in attributes.items():
            k_lower = str(k).lower()
            if any(s in k_lower for s in sensitive_keys):
                sanitized[k] = "[REDACTED]"
            else:
                sanitized[k] = Sanitizer.sanitize_data(v)
        return sanitized

    def start_span(self, name: str, attributes: dict[str, Any] | None = None) -> str:
        span_id = str(uuid.uuid4())
        sanitized_attrs = self._sanitize_attributes(attributes)

        # OpenTelemetry integration if enabled
        if self.otel_tracer:
            otel_span = self.otel_tracer.start_span(name, attributes=sanitized_attrs)
            self.spans[span_id] = {"name": name, "otel_span": otel_span}
        else:
            self.spans[span_id] = {"name": name}
        return span_id

    def end_span(self, span_id: str, success: bool = True, error: str | None = None):
        if span_id in self.spans:
            span_data = self.spans[span_id]
            otel_span = span_data.get("otel_span")
            if otel_span:
                if not success:
                    otel_span.set_status(Status(StatusCode.ERROR, error or "Error"))
                otel_span.end()
            # Clean up span from tracking
            del self.spans[span_id]

    @contextmanager
    def trace_span(self, name: str, attributes: dict[str, Any] | None = None):
        span_id = str(uuid.uuid4())
        sanitized_attrs = self._sanitize_attributes(attributes)

        otel_span = None
        ctx_mgr = None

        if self.otel_tracer:
            ctx_mgr = self.otel_tracer.start_as_current_span(
                name, attributes=sanitized_attrs
            )
            otel_span = ctx_mgr.__enter__()
            self.spans[span_id] = {"name": name, "otel_span": otel_span, "ctx_mgr": ctx_mgr}
        else:
            self.spans[span_id] = {"name": name}

        success = True
        error_msg = None
        try:
            yield otel_span
        except Exception as e:
            success = False
            error_msg = str(e)
            raise
        finally:
            if self.otel_tracer and span_id in self.spans:
                span_data = self.spans[span_id]
                ctx = span_data.get("ctx_mgr")
                if ctx:
                    if not success and otel_span is not None:
                        otel_span.set_status(Status(StatusCode.ERROR, error_msg or "Error"))
                    ctx.__exit__(None, None, None)
                del self.spans[span_id]
            elif span_id in self.spans:
                del self.spans[span_id]

    def get_trace_id(self) -> str:
        return self.trace_id
