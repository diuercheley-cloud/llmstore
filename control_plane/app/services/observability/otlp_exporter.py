# Owner: agent-platform
import logging
import os

from app.core.config import get_settings
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger(__name__)

class OTLPExporter:
    def setup(self, provider):
        settings = get_settings()
        if not settings.otlp_export_enabled:
            return

        endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317")
        exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        logger.info(f"OTLP exporter enabled, sending to {endpoint}")
