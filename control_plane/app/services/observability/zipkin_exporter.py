# Owner: agent-platform
import logging
import os

try:
    from opentelemetry.exporter.zipkin.proto.http import ZipkinExporter
except ImportError:
    ZipkinExporter = None
from app.core.config import get_settings
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger(__name__)


class ZipkinExporterService:
    def setup(self, provider):
        settings = get_settings()
        if not settings.zipkin_export_enabled:
            return

        if not ZipkinExporter:
            logger.warning(
                "Zipkin exporter is enabled in settings but opentelemetry-exporter-zipkin package is not installed."
            )
            return

        endpoint = os.environ.get("ZIPKIN_ENDPOINT", "http://localhost:9411/api/v2/spans")
        exporter = ZipkinExporter(endpoint=endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        logger.info(f"Zipkin exporter enabled, sending to {endpoint}")
