import os
import logging
from typing import Any, Dict, Optional
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class TracingService:
    _instance = None
    _tracer = None

    def __new__(cls):
        if not cls._instance:
            cls._instance = super(TracingService, cls).__new__(cls)
            cls._instance._setup()
        return cls._instance

    def _setup(self):
        settings = get_settings()
        resource = Resource.create({"service.name": "agentic-platform"})
        provider = TracerProvider(resource=resource)
        
        if settings.agent_otel_tracing_enabled:
            # Multi-exporter setup
            from app.services.observability.otlp_exporter import OTLPExporter
            from app.services.observability.jaeger_exporter import JaegerExporterService
            from app.services.observability.zipkin_exporter import ZipkinExporterService
            
            if settings.otlp_export_enabled:
                OTLPExporter().setup(provider)
            
            if settings.jaeger_export_enabled:
                JaegerExporterService().setup(provider)
                
            if settings.zipkin_export_enabled:
                ZipkinExporterService().setup(provider)

            if not any([settings.otlp_export_enabled, settings.jaeger_export_enabled, settings.zipkin_export_enabled]):
                # Default to console if none enabled but OTel is active
                provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        else:
            # Console only
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
            
        trace.set_tracer_provider(provider)
        self._tracer = trace.get_tracer("agent-runtime")

    def start_span(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        return self._tracer.start_as_current_span(name, attributes=attributes)

    def get_tracer(self):
        return self._tracer

tracing_service = TracingService()
