from app.models.agents.agent_tool_synthesis import AgentSandboxPolicyEvent, AgentSandboxSession
from sqlalchemy.orm import Session


class SandboxPolicy:
    def __init__(self, db: Session):
        self.db = db

    def check_approval(self, version_is_approved: bool, risk_level: str) -> bool:
        if risk_level == "high" and not version_is_approved:
            return False
        return True

    def create_policy_event(self, session_id, event_type: str, details: dict):
        event = AgentSandboxPolicyEvent(
            session_id=session_id, event_type=event_type, details=details
        )
        self.db.add(event)
        self.db.commit()
        return event

    def enforce_timeout(self, session: AgentSandboxSession):
        from app.core.time import utc_now

        if session.expires_at and utc_now() > session.expires_at:
            session.status = "expired"
            self.create_policy_event(
                session.id, "timeout", {"expired_at": session.expires_at.isoformat()}
            )
            self.db.commit()
            raise Exception("Sandbox session expired.")
