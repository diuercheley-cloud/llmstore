from typing import Any, Dict, List


class DeploymentsAPI:
    def __init__(self, client):
        self.client = client

    def create(self, agent_id: str, deployment_def: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", f"/{agent_id}/deployments", json=deployment_def)

    def list(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/deployments")

    def get(self, deployment_id: str) -> Dict[str, Any]:
        return self.client._request("GET", f"/deployments/{deployment_id}")

    def update(self, deployment_id: str, deployment_def: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("PATCH", f"/deployments/{deployment_id}", json=deployment_def)

    def pause(self, deployment_id: str) -> Dict[str, Any]:
        return self.client._request("POST", f"/deployments/{deployment_id}/pause")

    def resume(self, deployment_id: str) -> Dict[str, Any]:
        return self.client._request("POST", f"/deployments/{deployment_id}/resume")

    def archive(self, deployment_id: str) -> Dict[str, Any]:
        return self.client._request("POST", f"/deployments/{deployment_id}/archive")

    def rollback(self, deployment_id: str) -> Dict[str, Any]:
        return self.client._request("POST", f"/deployments/{deployment_id}/rollback")

    def get_usage(self, deployment_id: str) -> Dict[str, Any]:
        return self.client._request("GET", f"/deployments/{deployment_id}/usage")

    def get_sla(self, deployment_id: str) -> Dict[str, Any]:
        return self.client._request("GET", f"/deployments/{deployment_id}/sla")
