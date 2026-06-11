from typing import Any, List, Optional

from ...mas.schemas import AgentDefinition as HarnessAgentDef
from ...mas.schemas import AgentTeam, SubTask, TeamMember
from ..base import BaseConverter, ConvertResult
from .adapters import Agent, Crew, Task


class CrewAIConverter(BaseConverter[Crew, AgentTeam]):
    def __init__(self, default_model_profile: Optional[str] = None):
        self.default_model_profile = default_model_profile

    def _convert_agent(self, agent: Agent) -> HarnessAgentDef:
        backstory = agent.backstory or ""
        return HarnessAgentDef(
            role=agent.role,
            description=f"Goal: {agent.goal}" if agent.goal else agent.role,
            tools=[str(t) for t in agent.tools],
            prompt=f"Role: {agent.role}\nGoal: {agent.goal}\nBackstory: {backstory}",
            model_profile=self.default_model_profile,
        )

    def _convert_task(self, task: Task) -> SubTask:
        return SubTask(
            id=str(task.id),
            description=task.description,
            assigned_to=task.agent.role if task.agent else None,
            status="pending",
        )

    def convert(
        self,
        source: Crew,
        team_name: Optional[str] = None,
        topology: str = "linear",
        **kwargs: Any,
    ) -> ConvertResult[AgentTeam]:
        if not isinstance(source, Crew):
            return ConvertResult(
                success=False,
                error=f"Expected Crew instance, got {type(source).__name__}",
            )

        warnings: List[str] = []

        if source.process and "hierarchical" in source.process.lower():
            topology = "supervisor"
            warnings.append(
                "Hierarchical process detected. Converting to 'supervisor' topology. "
                "You may need to define a supervisor agent."
            )

        members = [
            TeamMember(agent_id=a.role, role=a.role)
            for a in source.agents
        ]

        team = AgentTeam(
            name=team_name or f"crewai_{source.process or 'sequential'}",
            description=f"Migrated CrewAI team ({len(source.agents)} agents, {len(source.tasks)} tasks)",
            members=members,
            topology=topology,
            shared_blackboard=True,
        )

        return ConvertResult(
            success=True,
            data=team,
            warnings=warnings,
        )

    def convert_batch(
        self,
        sources: List[Crew],
        **kwargs: Any,
    ) -> List[ConvertResult[AgentTeam]]:
        return [
            self.convert(crew, team_name=kwargs.get("team_name", f"crew_{i}"), **kwargs)
            for i, crew in enumerate(sources)
        ]
