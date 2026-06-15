from typing import Any, Dict, List


class ToolsAPI:
    def __init__(self, client):
        self.client = client

    def list(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/admin/agent-tools")

    def register(self, tool_def: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", "/admin/agent-tools", json=tool_def)

    def update(self, tool_id: str, tool_def: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("PATCH", f"/admin/agent-tools/{tool_id}", json=tool_def)

    def enable(self, tool_id: str) -> Dict[str, Any]:
        return self.client._request("POST", f"/admin/agent-tools/{tool_id}/enable")

    def disable(self, tool_id: str) -> Dict[str, Any]:
        return self.client._request("POST", f"/admin/agent-tools/{tool_id}/disable")

    def execute(self, tool_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", f"/admin/agent-tools/{tool_id}/execute", json=params)

    def dry_run(self, tool_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", f"/admin/agent-tools/{tool_id}/dry-run", json=params)

    def list_invocations(self, tool_id: str) -> List[Dict[str, Any]]:
        return self.client._request("GET", f"/admin/agent-tools/{tool_id}/invocations")

    def list_side_effects(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/admin/agent-tools/side-effects")

    def list_credentials(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/admin/agent-tools/credentials")

    def create_credential(self, credential: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", "/admin/agent-tools/credentials", json=credential)

    def revoke_credential(self, credential_id: str) -> Dict[str, Any]:
        return self.client._request(
            "POST", f"/admin/agent-tools/credentials/{credential_id}/revoke"
        )
