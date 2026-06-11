from typing import Any, Dict, List

from ...mas.schemas import AgentTeam, TeamMember
from ..base import BaseConverter, ConvertResult
from .adapters import ConversableAgent, GroupChat


def _extract_model_from_llm_config(llm_config: Dict[str, Any]) -> str:
    config_list = llm_config.get("config_list", [])
    if config_list and isinstance(config_list, list):
        first = config_list[0]
        if isinstance(first, dict):
            return first.get("model", "default-model")
    return "default-model"


class AutoGenConverter(BaseConverter[Any, AgentTeam]):
    def convert(
        self,
        source: Any,
        team_name: str = "autogen_migration",
        topology: str = "mesh",
        **kwargs: Any,
    ) -> ConvertResult[AgentTeam]:
        warnings: List[str] = []

        if isinstance(source, GroupChat):
            return self._convert_group_chat(source, team_name, topology, warnings)
        elif isinstance(source, ConversableAgent):
            return self._convert_single_agent(source, team_name, warnings)
        else:
            return ConvertResult(
                success=False,
                error=f"Expected ConversableAgent or GroupChat, got {type(source).__name__}",
            )

    def _convert_single_agent(
        self,
        agent: ConversableAgent,
        team_name: str,
        warnings: List[str],
    ) -> ConvertResult[AgentTeam]:
        if agent.code_execution_config:
            warnings.append(
                f"Agent '{agent.name}' has code_execution_config. "
                "Map to native sandbox tools after migration."
            )

        member = TeamMember(agent_id=agent.name, role=agent.name)
        team = AgentTeam(
            name=team_name,
            description=f"Migrated AutoGen single agent: {agent.name}",
            members=[member],
            topology="linear",
        )

        return ConvertResult(success=True, data=team, warnings=warnings)

    def _convert_group_chat(
        self,
        group_chat: GroupChat,
        team_name: str,
        topology: str,
        warnings: List[str],
    ) -> ConvertResult[AgentTeam]:
        if len(group_chat.agents) < 2:
            warnings.append("GroupChat has fewer than 2 agents.")

        members = []
        for agent in group_chat.agents:
            members.append(TeamMember(
                agent_id=agent.name,
                role=agent.name,
            ))
            if agent.code_execution_config:
                warnings.append(
                    f"Agent '{agent.name}' has code_execution_config. "
                    "Map to native sandbox tools."
                )

        description = (
            f"Migrated AutoGen GroupChat ({group_chat.speaker_selection_method} selection, "
            f"max {group_chat.max_round} rounds)"
        )

        team = AgentTeam(
            name=team_name,
            description=description,
            members=members,
            topology=topology,
        )

        return ConvertResult(success=True, data=team, warnings=warnings)

    def convert_batch(
        self,
        sources: List[Any],
        **kwargs: Any,
    ) -> List[ConvertResult[AgentTeam]]:
        return [
            self.convert(source, team_name=kwargs.get("team_name", f"autogen_{i}"), **kwargs)
            for i, source in enumerate(sources)
        ]
