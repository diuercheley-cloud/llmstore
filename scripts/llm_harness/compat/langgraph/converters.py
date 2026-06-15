from typing import Any

from ...mas.schemas import AgentDefinition, AgentTeam, TeamMember
from ..base import BaseConverter, ConvertResult
from .adapters import CompiledStateGraph, StateGraph


def _infer_agent_from_node(node_name: str, node_fn: Any) -> AgentDefinition:
    fn_doc = getattr(node_fn, "__doc__", None)
    return AgentDefinition(
        role=node_name,
        description=fn_doc or f"LangGraph node: {node_name}",
        tools=[],
        prompt=f"You are the '{node_name}' agent in a LangGraph workflow.\n\n{fn_doc or ''}",
        model_profile=None,
    )


class LangGraphConverter(BaseConverter[Any, AgentTeam]):
    def convert(
        self,
        source: Any,
        team_name: str = "langgraph_migration",
        topology: str = "linear",
        **kwargs: Any,
    ) -> ConvertResult[AgentTeam]:
        if isinstance(source, CompiledStateGraph):
            graph = source.graph
        elif isinstance(source, StateGraph):
            graph = source
        else:
            return ConvertResult(
                success=False,
                error=f"Expected StateGraph or CompiledStateGraph, got {type(source).__name__}",
            )

        warnings: list[str] = []
        members: list[TeamMember] = []
        agents: dict[str, AgentDefinition] = {}

        for node_name, node_fn in graph.nodes.items():
            agent_def = _infer_agent_from_node(node_name, node_fn)
            agents[node_name] = agent_def
            members.append(
                TeamMember(
                    agent_id=node_name,
                    role=node_name,
                )
            )

        if graph.conditional_edges:
            warnings.append(
                f"Conditional edges detected in graph. "
                f"Mapping to '{topology}' topology; conditions may need manual adjustment."
            )

        if not members:
            return ConvertResult(
                success=False,
                error="No nodes found in the state graph.",
            )

        team = AgentTeam(
            name=team_name,
            description=f"Migrated LangGraph workflow ({graph.entry_point} -> {graph.finish_point})",
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
        sources: list[Any],
        **kwargs: Any,
    ) -> list[ConvertResult[AgentTeam]]:
        return [
            self.convert(source, team_name=kwargs.get("team_name", f"graph_{i}"), **kwargs)
            for i, source in enumerate(sources)
        ]
