import json
import logging
from typing import Any

from ..coding_loop import CodingLoop
from ..model_router import ModelRouter
from ..models import ExecutionResult
from .blackboard import Blackboard
from .registry import AgentRegistry

logger = logging.getLogger(__name__)

class TeamOrchestrator:
    def __init__(self, coding_loop: CodingLoop):
        self.coding_loop = coding_loop
        self.config = coding_loop.config
        self.registry = AgentRegistry.load(self.config.agent_registry_file)
        self.router = ModelRouter(self.config)

    async def run_team(self, team_name: str, task: str) -> ExecutionResult:
        team = self.registry.get_team(team_name)
        if not team:
            raise ValueError(f"Team '{team_name}' not found in registry.")

        logger.info("Starting Team Execution: %s (Topology: %s)", team_name, team.topology)
        blackboard = Blackboard(task)
        self.coding_loop.current_team = team_name
        self.coding_loop.blackboard = blackboard
        
        try:
            if team.topology == "linear":
                return await self._run_linear(team, blackboard)
            elif team.topology == "supervisor":
                return await self._run_supervisor_team(team, blackboard)
            else:
                raise NotImplementedError(f"Topology '{team.topology}' not implemented.")
        finally:
            self.coding_loop.current_team = None
            self.coding_loop.blackboard = None

    async def _run_linear(self, team: Any, blackboard: Blackboard) -> ExecutionResult:
        """
        Runs members in the order they appear in the team definition.
        Each member receives the output of the previous one via blackboard summary.
        """
        last_result = None
        for member in team.members:
            agent_id = member.agent_id
            agent_def = self.registry.get_agent(agent_id)
            if not agent_def:
                logger.error("Agent '%s' not found for team member", agent_id)
                continue

            logger.info("Linear Flow: Calling agent '%s' (Role: %s)", agent_id, member.role)
            
            # Context for the agent
            instruction = f"Current role in team: {member.role}. Task: {blackboard.state.task}"
            if last_result:
                instruction += f"\n\nPrevious agent result: {last_result.message}"
            
            # Governance: Set allowed tools for this agent based on role or agent def
            # For now, we use agent_def.tools. In a future step, we could merge with role tools.
            self.coding_loop.current_agent = agent_id
            
            result = await self.coding_loop.run(
                instruction,
                system_override=agent_def.prompt,
                model_profile_override=member.model_profile or agent_def.model_profile
            )
            
            last_result = result
            blackboard.add_message(
                "System", agent_id, f"Executed linear step: {member.role}",
                {"success": result.success}
            )
            blackboard.add_message(
                agent_id, "Blackboard", result.message,
                {"metrics": result.metrics}
            )
            
            if not result.success and team.approval_policy == "strict":
                logger.warning("Linear execution stopped due to failure in strict mode")
                break

        return ExecutionResult(
            success=last_result.success if last_result else False,
            message=last_result.message if last_result else "No agents executed",
            events=[
                {"event": "team.timeline", "timeline": blackboard.generate_timeline()},
                {"event": "team.blackboard", "state": blackboard.state.model_dump(mode="json")},
                {"event": "team.report", "report": self._generate_team_report(team, blackboard)}
            ]
        )

    async def _run_supervisor_team(self, team: Any, blackboard: Blackboard) -> ExecutionResult:
        """
        Uses a supervisor agent (must be part of the team or the first member)
        to decide which member to call next.
        """
        # For simplicity, we assume the first member with role 'supervisor' is the supervisor.
        # If none found, we use a generic supervisor prompt with available members.
        supervisor_member = next((m for m in team.members if m.role == "supervisor"), team.members[0])
        supervisor_agent_id = supervisor_member.agent_id
        
        max_steps = 15
        for i in range(max_steps):
            logger.info("Team Supervisor Step %d/%d", i + 1, max_steps)
            
            # Call supervisor to decide next move
            decision = await self._call_team_supervisor(supervisor_agent_id, team, blackboard)
            if not decision:
                return ExecutionResult(success=False, message="Supervisor failed to make a decision")

            next_agent_id = decision.get("next_agent")
            instruction = decision.get("instruction", "")
            
            if decision.get("type") == "final" or next_agent_id == "final":
                 return ExecutionResult(
                    success=True,
                    message=decision.get("message", "Task completed by team"),
                    events=[
                        {"event": "team.timeline", "timeline": blackboard.generate_timeline()},
                        {"event": "team.blackboard", "state": blackboard.state.model_dump(mode="json")},
                        {"event": "team.report", "report": self._generate_team_report(team, blackboard)}
                    ]
                )

            # Validate next_agent_id is in team
            if not any(m.agent_id == next_agent_id for m in team.members):
                logger.warning("Supervisor chose agent '%s' not in team. Forcing finish.", next_agent_id)
                break

            agent_def = self.registry.get_agent(next_agent_id)
            self.coding_loop.current_agent = next_agent_id
            
            blackboard.add_message(supervisor_agent_id, next_agent_id, instruction)
            
            result = await self.coding_loop.run(
                instruction,
                system_override=agent_def.prompt,
                model_profile_override=agent_def.model_profile
            )
            
            blackboard.add_message(
                next_agent_id, supervisor_agent_id, result.message or "No message returned", 
                {"success": result.success}
            )
            
            # Update subtasks if any
            if "sub_task_id" in decision:
                from .schemas import SubTask
                st = SubTask(
                    id=decision["sub_task_id"],
                    description=instruction,
                    assigned_to=next_agent_id,
                    status="completed" if result.success else "failed",
                    result=result.message
                )
                blackboard.update_sub_task(st)

        return ExecutionResult(
            success=False,
            message="Supervisor reached max steps",
            events=[
                {"event": "team.timeline", "timeline": blackboard.generate_timeline()},
                {"event": "team.blackboard", "state": blackboard.state.model_dump(mode="json")},
                {"event": "team.report", "report": self._generate_team_report(team, blackboard)}
            ]
        )

    def _generate_team_report(self, team: Any, blackboard: Blackboard) -> str:
        lines = [
            f"# Team Report: {team.name}",
            f"**Description:** {team.description}",
            f"**Topology:** {team.topology}",
            "",
            "## Members",
            "| Agent ID | Role |",
            "|---|---|",
        ]
        for m in team.members:
            lines.append(f"| {m.agent_id} | {m.role} |")
        
        lines.append("")
        lines.append("## Timeline Summary")
        lines.append(blackboard.generate_timeline())
        
        lines.append("")
        lines.append("## Final Status")
        lines.append(f"Task: {blackboard.state.task}")
        
        return "\n".join(lines)

    async def _call_team_supervisor(self, supervisor_agent_id: str, team: Any, blackboard: Blackboard) -> dict:
        agent_def = self.registry.get_agent(supervisor_agent_id)
        members_info = [
            {"agent_id": m.agent_id, "role": m.role} for m in team.members if m.agent_id != supervisor_agent_id
        ]
        
        prompt = (
            f"{agent_def.prompt}\n\n"
            f"You are the supervisor for the team '{team.name}'.\n"
            f"Description: {team.description}\n"
            f"Members available:\n{json.dumps(members_info, indent=2)}\n\n"
            "Respond ONLY with a JSON object:\n"
            "{\n"
            '  "next_agent": "agent_id",\n'
            '  "instruction": "...",\n'
            '  "type": "action|final",\n'
            '  "sub_task_id": "optional_id",\n'
            '  "message": "if final"\n'
            "}\n\n"
            "IMPORTANT: If a member has already successfully completed the requested work (check the Blackboard messages and results), "
            'you MUST respond with "type": "final" and a completion message. DO NOT re-assign the same task repeatedly.\n\n'
            f"Task: {blackboard.state.task}\n"
            f"Blackboard State:\n{blackboard.to_summary()}"
        )

        messages = [{"role": "user", "content": prompt}]
        response = await self.router.chat_completion_with_fallback(
            messages,
            task_type="supervisor",
            profile_name=agent_def.model_profile,
            plain_chat=True
        )
        
        content = response["choices"][0]["message"]["content"]
        # Use helper from multi_agent or similar to parse JSON
        from ..multi_agent import _safe_parse_json
        return _safe_parse_json(content)
