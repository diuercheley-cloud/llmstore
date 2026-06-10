import uuid

from app.models.agents.agent_tool_synthesis import AgentGeneratedTool, AgentGeneratedToolVersion
from sqlalchemy.orm import Session


class GeneratedToolRegistry:
    def __init__(self, db: Session):
        self.db = db

    def register_tool(self, name: str, description: str, author_id: uuid.UUID = None) -> AgentGeneratedTool:
        tool = AgentGeneratedTool(name=name, description=description, author_agent_id=author_id)
        self.db.add(tool)
        self.db.commit()
        self.db.refresh(tool)
        return tool

    def add_tool_version(self, tool_id: uuid.UUID, version_tag: str, code: str, schema_json: dict = None) -> AgentGeneratedToolVersion:
        version = AgentGeneratedToolVersion(
            tool_id=tool_id,
            version_tag=version_tag,
            code=code,
            schema_json=schema_json
        )
        self.db.add(version)
        self.db.commit()
        self.db.refresh(version)
        return version

    def get_tool(self, tool_id: uuid.UUID) -> AgentGeneratedTool:
        return self.db.query(AgentGeneratedTool).filter(AgentGeneratedTool.id == tool_id).first()
    
    def approve_version(self, version_id: uuid.UUID, approver: str):
        version = self.db.query(AgentGeneratedToolVersion).filter(AgentGeneratedToolVersion.id == version_id).first()
        if version:
            from app.core.time import utc_now
            version.is_approved = True
            version.approved_by = approver
            version.approved_at = utc_now()
            self.db.commit()
            self.db.refresh(version)
        return version
