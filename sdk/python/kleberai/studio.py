from typing import Any, Dict, List


class StudioAPI:
    def __init__(self, client):
        self.client = client

    def create_flow(self, flow_def: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", "/admin/agents/studio/flows", json=flow_def)

    def list_flows(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/admin/agents/studio/flows")

    def get_flow(self, flow_id: str) -> Dict[str, Any]:
        return self.client._request("GET", f"/admin/agents/studio/flows/{flow_id}")

    def validate_flow(self, flow_id: str) -> Dict[str, Any]:
        return self.client._request("POST", f"/admin/agents/studio/flows/{flow_id}/validate")

    def compile_flow(self, flow_id: str) -> Dict[str, Any]:
        return self.client._request("POST", f"/admin/agents/studio/flows/{flow_id}/compile")

    def debug_run(self, run_id: str) -> Dict[str, Any]:
        return self.client._request("GET", f"/admin/agents/studio/debug/{run_id}")

    def create_version(self, flow_id: str, version_def: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", f"/admin/agents/studio/flows/{flow_id}/versions", json=version_def)

    def validate_version(self, version_id: str) -> Dict[str, Any]:
        return self.client._request("POST", f"/admin/agents/studio/versions/{version_id}/validate")

    def compile_version(self, version_id: str) -> Dict[str, Any]:
        return self.client._request("POST", f"/admin/agents/studio/versions/{version_id}/compile")

    def dry_run_version(self, version_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", f"/admin/agents/studio/versions/{version_id}/dry-run", json=params)

    def list_templates(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/admin/agents/studio/templates")

    def get_template(self, template_id: str) -> Dict[str, Any]:
        return self.client._request("GET", f"/admin/agents/studio/templates/{template_id}")

    def deploy_flow(self, flow_id: str) -> Dict[str, Any]:
        return self.client._request("POST", f"/admin/agents/studio/flows/{flow_id}/deploy")

    def get_dag(self, flow_id: str, version_id: str) -> Dict[str, Any]:
        return self.client._request("GET", f"/admin/agents/studio/flows/{flow_id}/versions/{version_id}/dag")
