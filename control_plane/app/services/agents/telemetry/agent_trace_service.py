# Owner: agent-platform
import logging
import uuid
from datetime import datetime
from typing import Any

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.agents.agents import AgentTrace
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class AgentTraceService:
    @classmethod
    def get_tracer(cls):
        return trace.get_tracer("agent.runtime.trace", "2.0.0")

    @classmethod
    async def create_trace(
        cls,
        db: AsyncSession,
        run_id: uuid.UUID,
        trace_type: str,  # reasoning_step, tool_call, memory_read, memory_write, retry, planning, review
        name: str,
        input_data: dict[str, Any] | None = None,
        output_data: dict[str, Any] | None = None,
        status: str = "success",
        error: str | None = None,
        duration_ms: float | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> AgentTrace:
        """
        Creates a trace span in OpenTelemetry/Tempo/Jaeger, and persists it to the DB table.
        """
        settings = get_settings()

        # 1. OpenTelemetry Span creation
        trace_id = None
        span_id = None

        start_dt = start_time or utc_now()
        end_dt = end_time or utc_now()

        if not duration_ms and start_dt and end_dt:
            duration_ms = (end_dt - start_dt).total_seconds() * 1000.0

        if settings.agent_otel_tracing_enabled:
            try:
                tracer = cls.get_tracer()
                # Start span
                with tracer.start_as_current_span(
                    name=f"agent.{trace_type}.{name}",
                    start_time=int(start_dt.timestamp() * 1e9),
                    attributes={
                        "gen_ai.run.id": str(run_id),
                        "gen_ai.trace.type": trace_type,
                        "gen_ai.status": status,
                    },
                ) as span:
                    ctx = span.get_span_context()
                    trace_id = format(ctx.trace_id, "032x")
                    span_id = format(ctx.span_id, "16x")

                    if input_data:
                        for k, v in input_data.items():
                            span.set_attribute(f"gen_ai.input.{k}", str(v))
                    if output_data:
                        for k, v in output_data.items():
                            span.set_attribute(f"gen_ai.output.{k}", str(v))
                    if error:
                        span.set_status(Status(StatusCode.ERROR, error))
                        span.set_attribute("error", error)
                    else:
                        span.set_status(Status(StatusCode.OK))
            except Exception as ex:
                logger.warning(f"Failed to create OTel span: {ex}")

        # 2. Database persistence
        trace_obj = AgentTrace(
            run_id=run_id,
            trace_id=trace_id,
            span_id=span_id,
            name=name,
            trace_type=trace_type,
            status=status,
            input_data=input_data,
            output_data=output_data,
            error=error,
            start_time=start_dt,
            end_time=end_dt,
            duration_ms=duration_ms,
        )
        db.add(trace_obj)
        await db.commit()
        await db.refresh(trace_obj)

        logger.info(f"[AGENT TRACE] Logged {trace_type} | Run: {run_id} | Status: {status}")
        return trace_obj
