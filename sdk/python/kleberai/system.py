from typing import Any, Dict, List


class SystemAPI:
    def __init__(self, client):
        self.client = client

    def health(self) -> Dict[str, Any]:
        return self.client._request("GET", "/health")

    def ready(self) -> Dict[str, Any]:
        return self.client._request("GET", "/ready")

    def status(self) -> Dict[str, Any]:
        return self.client._request("GET", "/status")

    def operational_readiness(self) -> Dict[str, Any]:
        return self.client._request("GET", "/operational-readiness")

    def deep_health(self) -> Dict[str, Any]:
        return self.client._request("GET", "/admin/health/deep")

    def capabilities(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/admin/capabilities")

    def runtime_summary(self) -> Dict[str, Any]:
        return self.client._request("GET", "/admin/runtime/summary")

    def get_cache_stats(self) -> Dict[str, Any]:
        return self.client._request("GET", "/admin/cache/stats")

    def invalidate_cache(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", "/admin/cache/invalidate", json=params)
