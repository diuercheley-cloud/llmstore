from typing import Any, Dict, List


class KnowledgeGraphAPI:
    def __init__(self, client):
        self.client = client

    def extract(self, text: str, **kwargs) -> Dict[str, Any]:
        payload = {"text": text, **kwargs}
        return self.client._request("POST", "/admin/agents/knowledge-graph/extract", json=payload)

    def list_entities(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/admin/agents/knowledge-graph/entities")

    def list_relations(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/admin/agents/knowledge-graph/relations")

    def query(self, query: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", "/admin/agents/knowledge-graph/query", json=query)

    def query_agent(self, agent_id: str, query: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", f"/agents/{agent_id}/knowledge/query", json=query)
