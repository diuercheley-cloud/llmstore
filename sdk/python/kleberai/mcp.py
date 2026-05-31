from typing import Any, Dict, List, Optional


class MCPAPI:
    def __init__(self, client):
        self.client = client

    def list_servers(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/admin/agents/mcp/servers")

    def register_server(self, server_def: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", "/admin/agents/mcp/servers", json=server_def)

    def discover_tools(self, server_id: str) -> Dict[str, Any]:
        return self.client._request("POST", f"/admin/agents/mcp/servers/{server_id}/discover")

    def approve_tool(self, server_id: str, tool_name: str) -> Dict[str, Any]:
        return self.client._request("POST", f"/admin/agents/mcp/servers/{server_id}/approve-tool", json={"tool_name": tool_name})

    def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", f"/admin/agents/mcp/tools/{tool_name}/call", json=params)

    def list_tools(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/admin/agents/mcp/tools")

    def get_audit_log(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/admin/agents/mcp/audit")

    def get_server_info(self) -> Dict[str, Any]:
        return self.client._request("GET", "/mcp")

    def list_server_tools(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/mcp/tools")

    def list_server_resources(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/mcp/resources")

    def list_server_prompts(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/mcp/prompts")

    def call_server_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", "/mcp/call", json=params)

    def register_oauth_client(self, client_def: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", "/admin/agents/mcp/oauth/clients", json=client_def)

    def create_oauth_grant(self, grant_def: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", "/admin/agents/mcp/oauth/grants", json=grant_def)

    def delete_oauth_grant(self, grant_id: str) -> Dict[str, Any]:
        return self.client._request("DELETE", f"/admin/agents/mcp/oauth/grants/{grant_id}")

    def oauth_token_exchange(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", "/admin/agents/mcp/oauth/token-exchange", json=params)

    def get_oauth_audit(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/admin/agents/mcp/oauth/audit")
