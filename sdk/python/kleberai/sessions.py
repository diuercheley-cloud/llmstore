from typing import Any, Dict, List, Optional


class SessionsAPI:
    def __init__(self, client):
        self.client = client

    def create(self, agent_id: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self.client._request("POST", f"/v1/agents/sessions/{agent_id}", json=params or {})

    def list(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/v1/agents/sessions")

    def get(self, session_id: str) -> Dict[str, Any]:
        return self.client._request("GET", f"/v1/agents/sessions/{session_id}")

    def delete(self, session_id: str) -> Dict[str, Any]:
        return self.client._request("DELETE", f"/v1/agents/sessions/{session_id}")

    def update(self, session_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("PATCH", f"/v1/agents/sessions/{session_id}", json=params)

    def send_message(self, session_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request(
            "POST", f"/v1/agents/sessions/{session_id}/messages", json=message
        )

    def list_messages(self, session_id: str) -> List[Dict[str, Any]]:
        return self.client._request("GET", f"/v1/agents/sessions/{session_id}/messages")

    def run(self, session_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request(
            "POST", f"/v1/agents/sessions/{session_id}/runs", json=input_data
        )
