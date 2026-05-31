import uuid
from typing import List, Optional, Dict, Any, Union


class AgentsAPI:
    def __init__(self, client):
        self.client = client

    def list(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/v1/agents")

    def create(self, manifest: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", "/v1/agents", json=manifest)

    def get(self, agent_id: Union[str, uuid.UUID]) -> Dict[str, Any]:
        return self.client._request("GET", f"/v1/agents/{agent_id}")

    def run(
        self,
        agent_id: Union[str, uuid.UUID],
        input_data: Dict[str, Any],
        correlation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload = {"input_data": input_data, "correlation_id": correlation_id}
        return self.client._request("POST", f"/v1/agents/{agent_id}/runs", json=payload)

    def get_run(self, run_id: Union[str, uuid.UUID]) -> Dict[str, Any]:
        return self.client._request("GET", f"/v1/agents/runs/{run_id}")

    def cancel_run(self, run_id: Union[str, uuid.UUID]) -> Dict[str, Any]:
        return self.client._request("POST", f"/v1/agents/runs/{run_id}/cancel")

    def stream_events(self, run_id: Union[str, uuid.UUID]):
        return self.client._request("GET", f"/v1/agents/runs/{run_id}/events")

    def update(self, agent_id: Union[str, uuid.UUID], manifest: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("PATCH", f"/admin/agents/{agent_id}", json=manifest)

    def activate(self, agent_id: Union[str, uuid.UUID]) -> Dict[str, Any]:
        return self.client._request("POST", f"/admin/agents/{agent_id}/activate")

    def deprecate(self, agent_id: Union[str, uuid.UUID]) -> Dict[str, Any]:
        return self.client._request("POST", f"/admin/agents/{agent_id}/deprecate")


class AgentEvalsAPI:
    def __init__(self, client):
        self.client = client

    def run(self, agent_id: Union[str, uuid.UUID], suite_id: Optional[str] = None) -> Dict[str, Any]:
        payload = {"suite_id": suite_id}
        return self.client._request("POST", f"/client/agents/{agent_id}/evals/run", json=payload)

    def create_dataset(self, dataset_def: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", "/admin/agent-evals/datasets", json=dataset_def)

    def create_dataset_version(self, dataset_id: str, version_def: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", f"/admin/agent-evals/datasets/{dataset_id}/versions", json=version_def)

    def get_reports(self, agent_id: Union[str, uuid.UUID]) -> List[Dict[str, Any]]:
        return self.client._request("GET", f"/admin/agent-evals/reports/{agent_id}")

    def run_admin(self, eval_def: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", "/admin/agent-evals/run", json=eval_def)

    def promotion_check(self, agent_id: Union[str, uuid.UUID]) -> Dict[str, Any]:
        return self.client._request("POST", f"/admin/agent-evals/promotion-check/{agent_id}")


class AdminAgentsAPI:
    def __init__(self, client):
        self.client = client

    def list(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/admin/agents")

    def create(self, agent_def: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", "/admin/agents", json=agent_def)

    def update(self, agent_id: Union[str, uuid.UUID], agent_def: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("PATCH", f"/admin/agents/{agent_id}", json=agent_def)

    def get_catalog(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/admin/agents/catalog")

    def list_budgets(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/admin/agents/budgets")

    def validate_budget(self, budget_def: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", "/admin/agents/budgets/validate", json=budget_def)

    def list_incident_playbooks(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/admin/agents/incidents/playbooks")

    def run_playbook(self, incident_id: str) -> Dict[str, Any]:
        return self.client._request("POST", f"/admin/agents/incidents/{incident_id}/run-playbook")

    def list_slo_classes(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/admin/agents/slo/classes")

    def get_slo_report(self) -> Dict[str, Any]:
        return self.client._request("GET", "/admin/agents/slo/report")

    def registry_list(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/admin/agent-registry")

    def registry_create(self, entry_def: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", "/admin/agent-registry", json=entry_def)

    def registry_get(self, entry_id: str) -> Dict[str, Any]:
        return self.client._request("GET", f"/admin/agent-registry/{entry_id}")

    def registry_approve(self, entry_id: str) -> Dict[str, Any]:
        return self.client._request("POST", f"/admin/agent-registry/{entry_id}/approve")

    def registry_activate(self, entry_id: str) -> Dict[str, Any]:
        return self.client._request("POST", f"/admin/agent-registry/{entry_id}/activate")

    def registry_pause(self, entry_id: str) -> Dict[str, Any]:
        return self.client._request("POST", f"/admin/agent-registry/{entry_id}/pause")

    def registry_deprecate(self, entry_id: str) -> Dict[str, Any]:
        return self.client._request("POST", f"/admin/agent-registry/{entry_id}/deprecate")

    def list_jobs(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/admin/agents/execution/jobs")

    def list_workers(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/admin/agents/execution/workers")

    def cancel_job(self, job_id: str) -> Dict[str, Any]:
        return self.client._request("POST", f"/admin/agents/execution/jobs/{job_id}/cancel")

    def retry_job(self, job_id: str) -> Dict[str, Any]:
        return self.client._request("POST", f"/admin/agents/execution/jobs/{job_id}/retry")

    def get_readiness(self) -> Dict[str, Any]:
        return self.client._request("GET", "/admin/agents/readiness")

    def run_readiness_check(self) -> Dict[str, Any]:
        return self.client._request("POST", "/admin/agents/readiness/run")

    def get_analytics_overview(self) -> Dict[str, Any]:
        return self.client._request("GET", "/api/v1/admin/agents/analytics/overview")

    def get_agent_analytics(self, agent_id: Union[str, uuid.UUID]) -> Dict[str, Any]:
        return self.client._request("GET", f"/api/v1/admin/agents/analytics/{agent_id}")

    def get_agent_costs(self, agent_id: Union[str, uuid.UUID]) -> Dict[str, Any]:
        return self.client._request("GET", f"/api/v1/admin/agents/analytics/{agent_id}/costs")

    def get_analytics_dashboard(self) -> Dict[str, Any]:
        return self.client._request("GET", "/api/v1/admin/agents/analytics/dashboard")

    def get_observability_overview(self) -> Dict[str, Any]:
        return self.client._request("GET", "/admin/agents/observability/overview")

    def get_run_timeline(self, run_id: str) -> Dict[str, Any]:
        return self.client._request("GET", f"/admin/agents/observability/runs/{run_id}/timeline")

    def get_run_trace(self, run_id: str) -> Dict[str, Any]:
        return self.client._request("GET", f"/admin/agents/observability/runs/{run_id}/trace")

    def get_metrics_summary(self) -> Dict[str, Any]:
        return self.client._request("GET", "/admin/agents/observability/metrics/summary")

    def get_telemetry_status(self) -> Dict[str, Any]:
        return self.client._request("GET", "/admin/agents/observability/telemetry/status")

    def export_traces(self, export_def: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", "/admin/agents/observability/traces/export", json=export_def)

    def a2a_discover(self) -> List[Dict[str, Any]]:
        return self.client._request("GET", "/admin/agents/a2a/discover")

    def a2a_get_profile(self, agent_id: str) -> Dict[str, Any]:
        return self.client._request("GET", f"/admin/agents/a2a/profile/{agent_id}")

    def a2a_announce(self, announcement: Dict[str, Any]) -> Dict[str, Any]:
        return self.client._request("POST", "/admin/agents/a2a/announce", json=announcement)
