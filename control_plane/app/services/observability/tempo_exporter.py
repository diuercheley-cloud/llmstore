# Owner: agent-platform
import logging

from app.core.config import get_settings
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger(__name__)


class TempoExporter:
    def setup(self, provider):
        settings = get_settings()
        if not getattr(settings, "tempo_export_enabled", False):
            return

        endpoint = getattr(settings, "tempo_endpoint", "http://localhost:4317")
        exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        logger.info(f"Tempo exporter enabled, sending to {endpoint}")
