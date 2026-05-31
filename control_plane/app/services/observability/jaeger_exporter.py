# Owner: agent-platform
import os
import logging
try:
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
except ImportError:
    JaegerExporter = None
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class JaegerExporterService:
    def setup(self, provider):
        settings = get_settings()
        if not settings.jaeger_export_enabled:
            return

        if not JaegerExporter:
            logger.warning("Jaeger exporter is enabled in settings but opentelemetry-exporter-jaeger package is not installed.")
            return

        agent_host = os.environ.get("JAEGER_AGENT_HOST", "localhost")
        agent_port = int(os.environ.get("JAEGER_AGENT_PORT", 6831))
        
        exporter = JaegerExporter(
            agent_host_name=agent_host,
            agent_port=agent_port,
        )
        provider.add_span_processor(BatchSpanProcessor(exporter))
        logger.info(f"Jaeger exporter enabled, sending to {agent_host}:{agent_port}")
