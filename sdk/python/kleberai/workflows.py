from typing import Any, Dict, List, Optional


class WorkflowsAPI:
    def __init__(self, client):
        self.client = client

    def create(self, workflow_def: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", "/admin/agents/workflows", json=workflow_def)

    def run(self, workflow_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", f"/admin/agents/workflows/{workflow_id}/run", json=input_data)

    def get_run(self, workflow_id: str, run_id: str) -> Dict[str, Any]:
        return self.client._request("GET", f"/admin/agents/workflows/{workflow_id}/run/{run_id}")

    def signal(self, workflow_id: str, run_id: str, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", f"/admin/agents/workflows/{workflow_id}/run/{run_id}/signal", json=signal_data)

    def cancel_run(self, workflow_id: str, run_id: str) -> Dict[str, Any]:
        return self.client._request("POST", f"/admin/agents/workflows/{workflow_id}/run/{run_id}/cancel")

    def list_external_events(self, workflow_id: str, run_id: str) -> List[Dict[str, Any]]:
        return self.client._request("GET", f"/admin/agents/workflows/{workflow_id}/run/{run_id}/external-events")
