import os
import yaml
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class AgentDefinition(BaseModel):
    role: str
    model_profile: Optional[str] = None
    description: Optional[str] = None
    tools: List[str] = Field(default_factory=list)
    prompt: str

class AgentRegistry(BaseModel):
    agents: Dict[str, AgentDefinition]
    risk_levels: List[str] = Field(default_factory=list)
    destructive_tools: List[str] = Field(default_factory=list)

    @classmethod
    def load(cls, file_path: str) -> "AgentRegistry":
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Agent registry file not found: {file_path}")
        
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        return cls(**data)

    def get_agent(self, agent_id: str) -> Optional[AgentDefinition]:
        return self.agents.get(agent_id)

    def is_tool_allowed(self, agent_id: str, tool_name: str) -> bool:
        agent = self.get_agent(agent_id)
        if not agent:
            return False
        # If 'all' is in tools, everything is allowed (if we want to support that)
        if "*" in agent.tools or "all" in agent.tools:
            return True
        return tool_name in agent.tools
