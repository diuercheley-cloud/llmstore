import os
import yaml
import logging
from typing import Dict, List, Optional
from pydantic import ValidationError

from .contracts import AgentTeam, TeamMember, AgentDefinition
from .registry import AgentRegistry

logger = logging.getLogger(__name__)


class TeamManager:
    def __init__(self, registry: AgentRegistry):
        self.registry = registry

    def load_team_from_yaml(self, file_path: str) -> AgentTeam:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Team definition file not found: {file_path}")
            
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            
        try:
            team = AgentTeam(**data)
            self.validate_team(team)
            return team
        except ValidationError as e:
            logger.error(f"Invalid team definition in {file_path}: {e}")
            raise

    def validate_team(self, team: AgentTeam):
        """Validates that all agents in the team exist in the registry."""
        for member in team.members:
            if not self.registry.get_agent(member.agent_id):
                raise ValueError(f"Agent '{member.agent_id}' not found in registry.")
        
        # Topology specific validations
        if team.topology == "planner_coder_reviewer":
            roles = [m.role for m in team.members]
            if not all(r in roles for r in ["planner", "coder", "reviewer"]):
                raise ValueError("Topology 'planner_coder_reviewer' requires agents with these exact roles.")
                
        return True

    def explain_team(self, team: AgentTeam) -> str:
        """Generates a human-readable explanation of the team structure and orchestration."""
        explanation = [
            f"Team: {team.team_name}",
            f"Description: {team.description}",
            f"Topology: {team.topology.replace('_', ' ').title()}",
            f"Max Iterations: {team.max_iterations}",
            "",
            "Members:"
        ]
        for m in team.members:
            agent = self.registry.get_agent(m.agent_id)
            explanation.append(f"  - {m.agent_id} as {m.role}")
            explanation.append(f"    Base Model: {agent.model_profile if agent else 'default'}")
            if m.permissions:
                explanation.append(f"    Permissions: {', '.join(m.permissions)}")
        
        return "\n".join(explanation)
