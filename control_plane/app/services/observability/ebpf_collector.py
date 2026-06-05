import logging
from typing import List, Optional
from app.services.observability.base import ObservabilityMetric, MetricType

logger = logging.getLogger(__name__)


class EBPFCollector:
    """
    Adapter for eBPF-based metric collection.
    Prepared for integration with BCC or libbpf.
    Currently returns 'unavailable' status if binary dependencies are missing.
    """
    def __init__(self):
        self._available = self._check_ebpf_support()

    def _check_ebpf_support(self) -> bool:
        try:
            # Check for common eBPF indicators in Linux
            import os
            return os.path.exists("/sys/kernel/debug/tracing")
        except Exception:
            return False

    def is_available(self) -> bool:
        return self._available

    async def collect_kernel_metrics(self) -> List[ObservabilityMetric]:
        if not self._available:
            return []

        # Placeholder for real eBPF collection logic
        # In a real implementation, we would read from BPF maps
        return [
            ObservabilityMetric(
                name="kernel.syscall_latency",
                value=0.5,
                type=MetricType.GAUGE,
                unit="ms",
                tags={"source": "ebpf"}
            ),
            ObservabilityMetric(
                name="kernel.network_throughput",
                value=1024.0,
                type=MetricType.COUNTER,
                unit="bytes",
                tags={"source": "ebpf"}
            )
        ]

    def get_status(self) -> str:
        return "active" if self._available else "unavailable"
