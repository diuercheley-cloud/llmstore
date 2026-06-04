import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class TraceExporter:
    """
    Generic trace exporter that dispatches to configured backends.
    Supports multiple export targets with configurable routing.
    """

    def __init__(self, backend: Optional[str] = None):
        self.backend = backend
        self._exporters = {}

    def _get_exporter(self, backend: str):
        if backend not in self._exporters:
            if backend == "phoenix":
                from app.services.agents.telemetry.phoenix_exporter import PhoenixExporter
                self._exporters[backend] = PhoenixExporter()
            elif backend == "langsmith":
                from app.services.agents.telemetry.langsmith_exporter import LangsmithExporter
                self._exporters[backend] = LangsmithExporter()
            else:
                logger.warning(f"Unknown trace backend: {backend}")
                return None
        return self._exporters.get(backend)

    def export(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        results = {"exported": False, "backends": {}}

        if self.backend:
            exporter = self._get_exporter(self.backend)
            if exporter:
                result = exporter.export(payload)
                results["backends"][self.backend] = result
                results["exported"] = results["exported"] or result.get("accepted", False)
        else:
            for backend in ["phoenix", "langsmith"]:
                exporter = self._get_exporter(backend)
                if exporter:
                    result = exporter.export(payload)
                    results["backends"][backend] = result
                    results["exported"] = results["exported"] or result.get("accepted", False)

        if not results["exported"]:
            results["reason"] = "no backend accepted the payload"

        return results

    def close(self):
        for backend, exporter in self._exporters.items():
            try:
                if hasattr(exporter, 'close'):
                    exporter.close()
            except Exception as e:
                logger.warning(f"Error closing {backend} exporter: {e}")
        self._exporters.clear()
