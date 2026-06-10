import uuid
from datetime import timedelta

from app.core.time import utc_now
from app.models.agents.agent_tool_synthesis import AgentSandboxSession
from app.services.agents.tool_synthesis.sandbox_runtime import SandboxRuntime
from sqlalchemy.orm import Session


class CodeInterpreter:
    def __init__(self, db: Session, allow_network: bool = False, allow_write: bool = False):
        self.db = db
        self.runtime = SandboxRuntime(db, allow_network, allow_write)

    def create_session(self, agent_id: uuid.UUID = None, ttl_seconds: int = 3600) -> AgentSandboxSession:
        expires_at = utc_now() + timedelta(seconds=ttl_seconds)
        session = AgentSandboxSession(agent_id=agent_id, expires_at=expires_at)
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def run_code(self, session_id: uuid.UUID, code: str, timeout_seconds: int = 5):
        # Retrieve session to ensure it exists and is active
        session = self.db.query(AgentSandboxSession).filter(AgentSandboxSession.id == session_id).first()
        if not session:
            raise ValueError("Sandbox session not found.")
        if session.status != "active":
            raise ValueError(f"Sandbox session is not active (status: {session.status}).")
            
        return self.runtime.execute_code(session_id, code, agent_id=session.agent_id, timeout_seconds=timeout_seconds)
