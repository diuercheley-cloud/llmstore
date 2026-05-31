"""
Owner: agent-platform
Status: beta
"""
import uuid
import logging
from datetime import timedelta
from typing import Any, Dict, Optional, List
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.agents import AgentIncident, AgentIncidentEvent, AgentIncidentLink
from app.core import metrics
from app.core.config import get_settings
from app.core.time import utc_now

logger = logging.getLogger(__name__)

class AgentIncidentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    async def detect_and_create_incident(
        self,
        tenant_id: str,
        agent_id: uuid.UUID,
        run_id: Optional[uuid.UUID],
        incident_type: str,
        title: str,
        severity: str = "medium",
        details: Optional[Dict[str, Any]] = None
    ) -> Optional[AgentIncident]:
        if not self.settings.agent_incident_response_enabled:
            return None

        # Check if open incident of same type exists for run
        if run_id:
            res = await self.db.execute(
                select(AgentIncident)
                .where(AgentIncident.run_id == run_id)
                .where(AgentIncident.incident_type == incident_type)
                .where(AgentIncident.status == "open")
            )
            existing = res.scalar_one_or_none()
            if existing:
                return existing

        details_json = details or {}
        # Security: redact secrets
        details_str = str(details_json).lower()
        if "secret" in details_str or "key" in details_str or "token" in details_str:
            details_json = {"sanitized": "Potential secrets redacted from incident details."}

        incident = AgentIncident(
            tenant_id=tenant_id,
            agent_id=agent_id,
            run_id=run_id,
            incident_type=incident_type,
            title=title,
            severity=severity,
            details_json=details_json,
            status="open",
            created_at=utc_now(),
            updated_at=utc_now()
        )
        self.db.add(incident)
        
        # Record metric
        metrics.LLM_AGENT_INCIDENTS_TOTAL.labels(
            agent_id=str(agent_id), incident_type=incident_type, severity=severity
        ).inc()

        logger.warning(f"Agent Incident created: {title} (type: {incident_type}, run: {run_id})")
        await self.db.commit()
        await self.db.refresh(incident)
        
        # Check for handoff loop or related incidents to link
        if incident_type == "handoff_loop":
            await self._link_related_incidents(incident)

        return incident

    async def _link_related_incidents(self, incident: AgentIncident):
        stmt = select(AgentIncident).where(
            AgentIncident.agent_id == incident.agent_id,
            AgentIncident.status == "open",
            AgentIncident.id != incident.id,
            AgentIncident.incident_type.in_(["handoff_loop", "tool_failure", "policy_denial"]),
        ).order_by(AgentIncident.created_at.desc()).limit(10)

        res = await self.db.execute(stmt)
        related = res.scalars().all()

        for rel in related:
            link = AgentIncidentLink(
                incident_id=incident.id,
                linked_incident_id=rel.id,
                link_type="related",
                created_at=utc_now(),
            )
            self.db.add(link)

        if related:
            logger.info(f"Linked {len(related)} related incidents to {incident.id}")
        else:
            logger.info(f"No related incidents found for {incident.id}, checking agent-level patterns")

            recent_stmt = select(AgentIncident).where(
                AgentIncident.agent_id == incident.agent_id,
                AgentIncident.created_at >= utc_now() - timedelta(hours=1),
            ).order_by(AgentIncident.created_at.desc())
            res2 = await self.db.execute(recent_stmt)
            recent_incidents = res2.scalars().all()

            if len(recent_incidents) >= 3:
                severity_escalation = AgentIncidentEvent(
                    incident_id=incident.id,
                    event_type="severity_escalated",
                    notes=f"Pattern detected: {len(recent_incidents)} incidents for agent in last hour",
                    created_at=utc_now(),
                )
                self.db.add(severity_escalation)
                incident.severity = "high"
                logger.warning(f"Incident {incident.id} severity escalated to high due to pattern")

    async def get_incident(self, incident_id: uuid.UUID) -> Optional[AgentIncident]:
        res = await self.db.execute(select(AgentIncident).where(AgentIncident.id == incident_id))
        return res.scalar_one_or_none()

    async def list_incidents(
        self,
        tenant_id: Optional[str] = None,
        agent_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AgentIncident]:
        query = select(AgentIncident).order_by(AgentIncident.created_at.desc())
        if tenant_id:
            query = query.where(AgentIncident.tenant_id == tenant_id)
        if agent_id:
            query = query.where(AgentIncident.agent_id == agent_id)
        if status:
            query = query.where(AgentIncident.status == status)
        
        query = query.offset(offset).limit(limit)
        res = await self.db.execute(query)
        return list(res.scalars().all())

    async def acknowledge_incident(self, incident_id: uuid.UUID, performed_by: str) -> AgentIncident:
        incident = await self.get_incident(incident_id)
        if not incident:
            raise ValueError("Incident not found")
        if incident.status == "resolved":
            raise ValueError("Cannot acknowledge a resolved incident")

        incident.status = "acknowledged"
        incident.acknowledged_by = performed_by
        incident.updated_at = utc_now()

        event = AgentIncidentEvent(
            incident_id=incident.id,
            event_type="acknowledged",
            performed_by=performed_by,
            created_at=utc_now()
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(incident)
        return incident

    async def resolve_incident(self, incident_id: uuid.UUID, performed_by: str, resolution_notes: str) -> AgentIncident:
        incident = await self.get_incident(incident_id)
        if not incident:
            raise ValueError("Incident not found")

        incident.status = "resolved"
        incident.resolved_by = performed_by
        incident.resolution_notes = resolution_notes
        incident.updated_at = utc_now()

        event = AgentIncidentEvent(
            incident_id=incident.id,
            event_type="resolved",
            performed_by=performed_by,
            notes=resolution_notes,
            created_at=utc_now()
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(incident)
        return incident
