import os

import yaml
from pydantic import BaseModel, Field

from .schemas import (
    AgentCapability,
    AgentDefinition,
    AgentRole,
    AgentTeam,
)


class AgentRegistry(BaseModel):
    agents: dict[str, AgentDefinition] = Field(default_factory=dict)
    teams: dict[str, AgentTeam] = Field(default_factory=dict)
    roles: dict[str, AgentRole] = Field(default_factory=dict)
    capabilities: dict[str, AgentCapability] = Field(default_factory=dict)
    risk_levels: list[str] = Field(default_factory=list)
    destructive_tools: list[str] = Field(default_factory=list)

    @classmethod
    def load(cls, file_path: str) -> "AgentRegistry":
        if not os.path.exists(file_path):
            # Return empty registry if file doesn't exist to avoid breaking everything
            return cls()

        with open(file_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data:
            return cls()

        return cls(**data)

    def get_agent(self, agent_id: str) -> AgentDefinition | None:
        return self.agents.get(agent_id)

    def get_team(self, team_name: str) -> AgentTeam | None:
        return self.teams.get(team_name)

    def is_tool_allowed(self, agent_id: str, tool_name: str) -> bool:
        agent = self.get_agent(agent_id)
        if not agent:
            return False
        # If 'all' is in tools, everything is allowed
        if "*" in agent.tools or "all" in agent.tools:
            return True
        return tool_name in agent.tools

    def is_tool_allowed_for_team_member(
        self, team_name: str, agent_id: str, tool_name: str
    ) -> bool:
        if tool_name == "final":
            return True

        team = self.get_team(team_name)
        if not team:
            return self.is_tool_allowed(agent_id, tool_name)

        member = next((m for m in team.members if m.agent_id == agent_id), None)
        if not member:
            return False

        # Check role-based tools if role is defined in registry
        role_def = self.roles.get(member.role)
        if role_def and role_def.allowed_tools:
            if "*" in role_def.allowed_tools or "all" in role_def.allowed_tools:
                return True
            if tool_name in role_def.allowed_tools:
                return True

        # Fallback to agent's own tools
        return self.is_tool_allowed(agent_id, tool_name)

    def get_tool_risk_level(self, tool_name: str) -> str:
        if tool_name in self.destructive_tools:
            return "destructive"
        if tool_name in {"run_shell", "terminal_command"}:
            return "shell"
        if tool_name in {"write_file", "apply_patch", "replace_content"}:
            return "write"
        if tool_name in {"read_file", "list_dir", "grep", "index_query"}:
            return "read"
        if "network" in tool_name or "http" in tool_name:
            return "network"
        return "unknown"

    def validate(self):
        """
        Validates the registry for consistency.
        - Team members must refer to existing agents.
        - Team members must refer to existing roles (if roles are defined).
        """
        errors = []
        for team_name, team in self.teams.items():
            for member in team.members:
                if member.agent_id not in self.agents:
                    errors.append(
                        f"Team '{team_name}' member agent '{member.agent_id}' not found in agents."
                    )
                if self.roles and member.role not in self.roles:
                    errors.append(
                        f"Team '{team_name}' member role '{member.role}' not found in roles."
                    )

        if errors:
            raise ValueError("\n".join(errors))
        return True
