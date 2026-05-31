import uuid
from typing import Any, Dict, List, Optional


class MemoryAPI:
    def __init__(self, client):
        self.client = client

    def list_policies(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/admin/agents/memory/policies")

    def create_policy(self, policy: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", "/admin/agents/memory/policies", json=policy)

    def list_consents(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/admin/agents/memory/consents")

    def create_consent(self, consent: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", "/admin/agents/memory/consents", json=consent)

    def search(self, query: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", "/admin/agents/memory/search", json=query)

    def export(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", "/admin/agents/memory/export", json=params)

    def delete_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", "/admin/agents/memory/delete-request", json=request)

    def run_retention(self) -> Dict[str, Any]:
        return self.client._request("POST", "/admin/agents/memory/retention/run")

    def list_access_events(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/admin/agents/memory/access-events")

    def list_items(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/admin/agents/memory/items")

    def delete_item(self, item_id: str) -> Dict[str, Any]:
        return self.client._request("DELETE", f"/admin/agents/memory/items/{item_id}")

    def get_cognitive(self) -> Dict[str, Any]:
        return self.client._request("GET", "/admin/agents/memory/cognitive")

    def summarize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", "/admin/agents/memory/summarize", json=params)

    def explain(self, memory_id: str) -> Dict[str, Any]:
        return self.client._request("GET", f"/admin/agents/memory/explain/{memory_id}")
