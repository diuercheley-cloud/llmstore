import pytest
from unittest.mock import MagicMock, patch
from app.services.observability.jaeger_exporter import JaegerExporterService
from app.services.observability.zipkin_exporter import ZipkinExporterService
from app.core.config import Settings

@pytest.fixture
def settings():
    return Settings(
        jaeger_export_enabled=True,
        zipkin_export_enabled=True
    )

def test_jaeger_exporter_setup_no_package():
    with patch("app.services.observability.jaeger_exporter.JaegerExporter", None), \
         patch("app.services.observability.jaeger_exporter.get_settings") as mock_settings:
        mock_settings.return_value = Settings(jaeger_export_enabled=True)
        service = JaegerExporterService()
        provider = MagicMock()
        # Should not raise even if package is missing
        service.setup(provider)
        provider.add_span_processor.assert_not_called()

def test_zipkin_exporter_setup_no_package():
    with patch("app.services.observability.zipkin_exporter.ZipkinExporter", None), \
         patch("app.services.observability.zipkin_exporter.get_settings") as mock_settings:
        mock_settings.return_value = Settings(zipkin_export_enabled=True)
        service = ZipkinExporterService()
        provider = MagicMock()
        # Should not raise even if package is missing
        service.setup(provider)
        provider.add_span_processor.assert_not_called()

def test_exporters_disabled():
    with patch("app.services.observability.jaeger_exporter.get_settings") as mock_settings_j, \
         patch("app.services.observability.zipkin_exporter.get_settings") as mock_settings_z:
        mock_settings_j.return_value = Settings(jaeger_export_enabled=False)
        mock_settings_z.return_value = Settings(zipkin_export_enabled=False)
        
        j_service = JaegerExporterService()
        z_service = ZipkinExporterService()
        provider = MagicMock()
        
        j_service.setup(provider)
        z_service.setup(provider)
        
        provider.add_span_processor.assert_not_called()
