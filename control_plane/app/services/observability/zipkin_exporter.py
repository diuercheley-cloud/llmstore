# Owner: agent-platform
import os
import logging
from opentelemetry.exporter.zipkin.proto.http import ZipkinExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class ZipkinExporterService:
    def setup(self, provider):
        settings = get_settings()
        if not settings.zipkin_export_enabled:
            return

        endpoint = os.environ.get("ZIPKIN_ENDPOINT", "http://localhost:9411/api/v2/spans")
        exporter = ZipkinExporter(endpoint=endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        logger.info(f"Zipkin exporter enabled, sending to {endpoint}")
