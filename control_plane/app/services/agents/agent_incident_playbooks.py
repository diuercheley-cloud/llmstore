# Owner: agent-platform
import logging
import uuid
from typing import Any, Dict, List

from app.core.time import utc_now
from app.models.agents.agents import AgentIncident
from app.services.admin_rbac import record_admin_audit_event
from app.services.agents import agent_state
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class AgentIncidentPlaybookService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_available_playbooks(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "runaway-agent",
                "name": "Runaway Agent Mitigation",
                "description": "Termina execuções em loop ou excessivamente longas.",
                "destructive": True,
                "required_role": "admin_write"
            },
            {
                "id": "tool-cascade-failure",
                "name": "Tool Isolation",
                "description": "Desabilita ferramentas que estão causando falhas sistêmicas.",
                "destructive": True,
                "required_role": "admin_write"
            },
            {
                "id": "memory-poisoning",
                "name": "Memory Quarantine",
                "description": "Isola memórias corrompidas ou maliciosas.",
                "destructive": True,
                "required_role": "admin_write"
            },
            {
                "id": "stuck-approvals",
                "name": "Approval Expiry",
                "description": "Expira aprovações pendentes há muito tempo.",
                "destructive": True,
                "required_role": "admin_write"
            },
            {
                "id": "queue-saturation",
                "name": "Queue Throttling",
                "description": "Limita a entrada de novos jobs para aliviar a carga.",
                "destructive": True,
                "required_role": "admin_write"
            }
        ]

    async def execute_playbook(
        self,
        incident_id: uuid.UUID,
        playbook_id: str,
        performed_by: str,
        confirmation: bool = False
    ) -> Dict[str, Any]:
        incident = await self.db.get(AgentIncident, incident_id)
        if not incident:
            raise ValueError("Incident not found")

        playbooks = await self.list_available_playbooks()
        playbook = next((p for p in playbooks if p["id"] == playbook_id), None)
        if not playbook:
            raise ValueError(f"Playbook {playbook_id} not found")

        if playbook["destructive"] and not confirmation:
            raise ValueError("Destructive playbook requires confirmation")

        # Initial Report
        report = {
            "before": {
                "incident_status": incident.status,
                "incident_type": incident.incident_type,
                "run_id": str(incident.run_id) if incident.run_id else None
            },
            "actions": [],
            "after": {}
        }

        # Playbook logic
        if playbook_id == "runaway-agent":
            if incident.run_id:
                await agent_state.update_run(self.db, incident.run_id, status="failed", failure_reason="Terminated by runaway-agent playbook")
                report["actions"].append(f"Killed run {incident.run_id}")
            else:
                report["actions"].append("No run_id associated with incident")

        elif playbook_id == "tool-cascade-failure":
            tool_name = incident.details_json.get("tool_name")
            if tool_name:
                # In a real system, we'd update a global tool state
                report["actions"].append(f"Disabled tool {tool_name} (simulated)")
            else:
                report["actions"].append("No tool_name found in incident details")

        elif playbook_id == "memory-poisoning":
            # Logic to move items to tombstone
            report["actions"].append(f"Quarantined memory for agent {incident.agent_id} (simulated)")

        elif playbook_id == "stuck-approvals":
            # Logic to expire approvals
            report["actions"].append("Expired stale approvals (simulated)")

        elif playbook_id == "queue-saturation":
            # Logic to throttle
            report["actions"].append("Applied queue throttle limit (simulated)")

        # Audit Event
        await record_admin_audit_event(
            self.db,
            event_type=f"agent.playbook.{playbook_id}",
            status="success",
            actor_identifier=performed_by,
            target_type="agent_incident",
            target_id=str(incident_id),
            metadata={"report": report}
        )

        # Update Incident
        incident.status = "resolved"
        incident.resolved_by = performed_by
        incident.resolution_notes = f"Playbook {playbook_id} executed by {performed_by}."
        incident.updated_at = utc_now()
        
        await self.db.commit()

        report["after"] = {
            "incident_status": incident.status,
            "resolved_at": incident.updated_at.isoformat()
        }

        return report
