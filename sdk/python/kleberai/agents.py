import uuid
from typing import List, Optional, Dict, Any, Union

class AgentsAPI:
    def __init__(self, client):
        self.client = client

    def list(self) -> List[Dict[str, Any]]:
        """List all agents available to the tenant."""
        return self.client._request("GET", "/client/agents")

    def create(self, manifest: Dict[str, Any]) -> Dict[str, Any]:
        """Register a new agent from a manifest."""
        return self.client._request("POST", "/client/agents", json=manifest)

    def run(
        self, 
        agent_id: Union[str, uuid.UUID], 
        input_data: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Start a new agent execution run."""
        payload = {
            "input_data": input_data,
            "correlation_id": correlation_id
        }
        return self.client._request("POST", f"/client/agents/{agent_id}/run", json=payload)

    def get_run(self, run_id: Union[str, uuid.UUID]) -> Dict[str, Any]:
        """Get the status and details of an agent run."""
        return self.client._request("GET", f"/client/agents/runs/{run_id}")

    def cancel_run(self, run_id: Union[str, uuid.UUID]) -> Dict[str, Any]:
        """Cancel an ongoing agent run."""
        return self.client._request("POST", f"/client/agents/runs/{run_id}/cancel")

    def stream_events(self, run_id: Union[str, uuid.UUID]):
        """Stream execution events for a run (Mock implementation for now)."""
        # In a real implementation, this would use Server-Sent Events (SSE)
        return self.client._request("GET", f"/client/agents/runs/{run_id}/events")

class AgentEvalsAPI:
    def __init__(self, client):
        self.client = client

    def run(self, agent_id: Union[str, uuid.UUID], suite_id: Optional[str] = None) -> Dict[str, Any]:
        """Run an evaluation suite for an agent."""
        payload = {"suite_id": suite_id}
        return self.client._request("POST", f"/client/agents/{agent_id}/evals/run", json=payload)
