import json
import logging

from ..coding_loop import CodingLoop
from ..model_router import ModelRouter
from ..models import ExecutionResult
from .blackboard import Blackboard
from .contracts import AgentTeam, TeamMember
from .registry import AgentRegistry

logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self, coding_loop: CodingLoop):
        self.coding_loop = coding_loop
        self.config = coding_loop.config
        self.registry = AgentRegistry.load(self.config.agent_registry_file)
        self.router = ModelRouter(self.config)

    async def run(self, team: AgentTeam, task: str) -> ExecutionResult:
        blackboard = Blackboard(task)
        self.coding_loop.blackboard = blackboard

        logger.info(f"Orchestrating team '{team.team_name}' with topology '{team.topology}'")

        try:
            if team.topology == "planner_coder_reviewer":
                return await self._run_pcr(team, blackboard)
            elif team.topology == "debate":
                return await self._run_debate(team, blackboard)
            elif team.topology == "supervisor":
                return await self._run_supervisor(team, blackboard)
            elif team.topology == "hierarchical":
                return await self._run_hierarchical(team, blackboard)
            elif team.topology == "parallel_dry_run":
                return await self._run_parallel_dry_run(team, blackboard)
            else:
                # Fallback to simple sequential/linear if unknown
                return await self._run_sequential(team, blackboard)
        finally:
            self.coding_loop.blackboard = None

    async def _run_pcr(self, team: AgentTeam, blackboard: Blackboard) -> ExecutionResult:
        """Planner-Coder-Reviewer loop."""
        planner = next(m for m in team.members if m.role == "planner")
        coder = next(m for m in team.members if m.role == "coder")
        reviewer = next(m for m in team.members if m.role == "reviewer")

        # 1. Plan
        plan_result = await self._call_agent(
            planner, blackboard, "Create a detailed plan for the task."
        )
        blackboard.add_message(planner.agent_id, "blackboard", plan_result.message)

        for i in range(team.max_iterations):
            # 2. Code
            code_result = await self._call_agent(coder, blackboard, "Implement the current plan.")
            blackboard.add_message(coder.agent_id, "blackboard", code_result.message)

            # 3. Review
            review_result = await self._call_agent(
                reviewer, blackboard, "Review the implementation against the plan."
            )
            blackboard.add_message(reviewer.agent_id, "blackboard", review_result.message)

            if (
                "LGTM" in review_result.message.upper()
                or "APPROVED" in review_result.message.upper()
            ):
                return ExecutionResult(success=True, message=code_result.message)

        return ExecutionResult(
            success=False, message="PCR loop reached max iterations without approval."
        )

    async def _run_debate(self, team: AgentTeam, blackboard: Blackboard) -> ExecutionResult:
        """Two or more agents debating a solution."""
        for i in range(team.max_iterations):
            for member in team.members:
                prompt = f"Iteration {i + 1}. Current debate state on blackboard. Provide your perspective or critique."
                result = await self._call_agent(member, blackboard, prompt)
                blackboard.add_message(member.agent_id, "debate", result.message)

                # Check stop conditions
                for condition in team.stop_conditions:
                    if condition.lower() in result.message.lower():
                        return ExecutionResult(success=True, message=result.message)

        return ExecutionResult(success=True, message="Debate concluded after max iterations.")

    async def _run_supervisor(self, team: AgentTeam, blackboard: Blackboard) -> ExecutionResult:
        # Implementation similar to existing supervisor in team_orchestrator.py
        supervisor = team.members[0]  # Assume first is supervisor

        for i in range(team.max_iterations):
            # 1. Supervisor decides
            decision = await self._get_supervisor_decision(supervisor, team, blackboard)
            if decision.get("type") == "final":
                return ExecutionResult(success=True, message=decision.get("message"))

            # 2. Execute decision
            next_agent_id = decision.get("next_agent")
            member = next(m for m in team.members if m.agent_id == next_agent_id)
            await self._call_agent(member, blackboard, decision.get("instruction"))

        return ExecutionResult(success=False, message="Supervisor reached max iterations.")

    async def _run_hierarchical(self, team: AgentTeam, blackboard: Blackboard) -> ExecutionResult:
        """Manager delegates to sub-teams or individuals."""
        # Simplified for now: Top agent acts as manager
        return await self._run_supervisor(team, blackboard)

    async def _run_sequential(self, team: AgentTeam, blackboard: Blackboard) -> ExecutionResult:
        last_msg = ""
        for member in team.members:
            res = await self._call_agent(member, blackboard, f"Previous output: {last_msg}")
            last_msg = res.message
            blackboard.add_message(member.agent_id, "sequence", last_msg)
        return ExecutionResult(success=True, message=last_msg)

    async def _run_parallel_dry_run(
        self, team: AgentTeam, blackboard: Blackboard
    ) -> ExecutionResult:
        """All agents run in parallel (simulated) and results are compared."""
        results = {}
        for member in team.members:
            # In a real system this would be async gather
            res = await self._call_agent(
                member, blackboard, "Provide your best solution. (Dry-run mode)"
            )
            results[member.agent_id] = res.message

        return ExecutionResult(
            success=True, message=f"Parallel Dry-run complete. Results: {json.dumps(results)}"
        )

    async def _call_agent(
        self, member: TeamMember, blackboard: Blackboard, instruction: str
    ) -> ExecutionResult:
        agent_def = self.registry.get_agent(member.agent_id)

        # Enforce permissions (simplified: add to system prompt)
        perm_string = f"Your permissions: {', '.join(member.permissions or agent_def.tools)}"

        context = blackboard.to_summary()
        full_prompt = f"{instruction}\n\n{context}\n\n{perm_string}"

        self.coding_loop.current_agent = member.agent_id
        return await self.coding_loop.run(
            full_prompt,
            system_override=agent_def.prompt,
            model_profile_override=member.model_profile or agent_def.model_profile,
        )

    async def _get_supervisor_decision(
        self, supervisor: TeamMember, team: AgentTeam, blackboard: Blackboard
    ) -> dict:
        agent_def = self.registry.get_agent(supervisor.agent_id)
        members_info = [{"id": m.agent_id, "role": m.role} for m in team.members if m != supervisor]

        prompt = (
            f"Supervisor decision time. Blackboard summary:\n{blackboard.to_summary()}\n"
            f"Available agents: {json.dumps(members_info)}\n"
            'Return JSON: {"type": "action|final", "next_agent": "id", "instruction": "...", "message": "..."}'
        )

        res = await self.router.chat_completion_with_fallback(
            [{"role": "user", "content": prompt}],
            profile_name=agent_def.model_profile,
            plain_chat=True,
        )
        content = res["choices"][0]["message"]["content"]

        from ..multi_agent import _safe_parse_json

        return _safe_parse_json(content) or {
            "type": "final",
            "message": "Failed to parse supervisor decision.",
        }
