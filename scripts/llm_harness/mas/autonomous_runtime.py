import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..checkpoint import CheckpointManager
from ..coding_loop import CodingLoop
from ..model_router import ModelRouter
from ..models import ExecutionResult
from .blackboard import Blackboard
from .registry import AgentRegistry

logger = logging.getLogger(__name__)

class AutonomousAgentRuntime:
    def __init__(self, coding_loop: CodingLoop):
        self.coding_loop = coding_loop
        self.config = coding_loop.config
        self.registry = AgentRegistry.load(self.config.agent_registry_file)
        self.router = ModelRouter(self.config)
        self.checkpoint_manager = CheckpointManager(self.config.checkpoint_dir)
        self.runs: Dict[str, Dict[str, Any]] = {}

    async def run_autonomous(
        self, 
        agent_id: Optional[str] = None, 
        team_name: Optional[str] = None, 
        goal: str = "",
        max_steps: int = 50,
        budget: Optional[float] = None,
        cooldown: int = 60,
        resume_run_id: Optional[str] = None
    ) -> ExecutionResult:
        run_id = resume_run_id or f"auto-{int(time.time())}"
        
        if resume_run_id:
            state = self.checkpoint_manager.load_checkpoint(resume_run_id)
            if not state:
                return ExecutionResult(success=False, message=f"Run ID {resume_run_id} not found")
            from .schemas import BlackboardState
            blackboard = Blackboard(state["task"])
            blackboard.state = BlackboardState(**state["blackboard_state"])
            current_step = state.get("current_step", 0)
            total_cost = state.get("total_cost", 0.0)
            total_tokens = state.get("total_tokens", 0)
        else:
            blackboard = Blackboard(goal)
            current_step = 0
            total_cost = 0.0
            total_tokens = 0
            
        self.runs[run_id] = {
            "status": "running",
            "agent_id": agent_id,
            "team_name": team_name,
            "goal": goal,
            "current_step": current_step,
            "blackboard": blackboard
        }

        logger.info("Starting Autonomous Run: %s", run_id)
        
        for step in range(current_step, max_steps):
            if self.runs[run_id]["status"] == "paused":
                logger.info("Run %s paused", run_id)
                self._save_state(run_id, step, total_cost, total_tokens)
                return ExecutionResult(success=True, message=f"Run {run_id} paused at step {step}")

            if self.runs[run_id]["status"] == "stopped":
                logger.info("Run %s stopped", run_id)
                return ExecutionResult(success=True, message=f"Run {run_id} stopped manually")

            logger.info("Autonomous Step %d/%d for Run %s", step + 1, max_steps, run_id)
            
            # Observe & Decide
            decision = await self._decide(agent_id, team_name, blackboard)
            if not decision:
                return ExecutionResult(success=False, message="Failed to make a decision")

            if decision.get("type") == "final":
                logger.info("Autonomous goal achieved: %s", decision.get("message"))
                self._save_state(run_id, step, total_cost, total_tokens)
                return ExecutionResult(success=True, message=decision.get("message"))

            if decision.get("type") == "wait":
                wait_time = decision.get("seconds", cooldown)
                logger.info("Decision to wait for %d seconds", wait_time)
                await asyncio.sleep(wait_time)
                continue

            # Act
            instruction = decision.get("instruction", "")
            target_agent = decision.get("next_agent") or agent_id
            
            if not target_agent:
                 return ExecutionResult(success=False, message="No agent specified for action")

            agent_def = self.registry.get_agent(target_agent)
            self.coding_loop.current_agent = target_agent
            self.coding_loop.blackboard = blackboard
            
            result = await self.coding_loop.run(
                instruction,
                system_override=agent_def.prompt if agent_def else None,
                model_profile_override=agent_def.model_profile if agent_def else None
            )
            
            total_cost += result.metrics.get("estimated_cost", 0.0) if result.metrics else 0.0
            total_tokens += result.metrics.get("total_tokens", 0) if result.metrics else 0
            
            # Budget check
            if budget and total_cost > budget:
                logger.warning(
                    "Budget exceeded for run %s: %.4f > %.4f", run_id, total_cost, budget
                )
                self._save_state(run_id, step, total_cost, total_tokens)
                return ExecutionResult(success=False, message=f"Budget exceeded: {total_cost}")

            # Record
            blackboard.add_message("Runtime", target_agent, f"Step {step+1}: {instruction}")
            blackboard.add_message(
                target_agent, "Runtime", result.message, {"success": result.success}
            )
            
            # Checkpoint
            if self.config.checkpoint_every_step:
                self._save_state(run_id, step + 1, total_cost, total_tokens)

            # Cooldown
            if cooldown > 0:
                await asyncio.sleep(cooldown)

        return ExecutionResult(success=False, message="Max steps reached")

    def _save_state(self, run_id: str, step: int, cost: float, tokens: int):
        run_data = self.runs[run_id]
        state = {
            "run_id": run_id,
            "status": run_data["status"],
            "agent_id": run_data["agent_id"],
            "team_name": run_data["team_name"],
            "task": run_data["goal"],
            "current_step": step,
            "total_cost": cost,
            "total_tokens": tokens,
            "blackboard_state": run_data["blackboard"].state.model_dump(mode="json"),
            "timestamp": datetime.now().isoformat()
        }
        self.checkpoint_manager.save_checkpoint(run_id, state)

    async def _decide(
        self, agent_id: Optional[str], team_name: Optional[str], blackboard: Blackboard
    ) -> dict:
        # Use a high-reasoning model for decision if possible
        available_agents = []
        if team_name:
            team = self.registry.get_team(team_name)
            available_agents = [{"id": m.agent_id, "role": m.role} for m in team.members]
        elif agent_id:
            agent_def = self.registry.get_agent(agent_id)
            available_agents = [{"id": agent_id, "role": agent_def.role}]

        prompt = (
            "You are an Autonomous Orchestrator.\n"
            f"Goal: {blackboard.state.task}\n"
            "Available Agents:\n"
            f"{json.dumps(available_agents, indent=2)}\n\n"
            "Respond ONLY with a JSON object:\n"
            "{\n"
            '  "type": "action|wait|final",\n'
            '  "next_agent": "agent_id",\n'
            '  "instruction": "what to do next",\n'
            '  "seconds": 60, // if wait\n'
            '  "message": "if final"\n'
            "}\n\n"
            f"Current State:\n{blackboard.to_summary()}"
        )
        
        messages = [{"role": "user", "content": prompt}]
        response = await self.router.chat_completion_with_fallback(
            messages,
            task_type="supervisor",
            plain_chat=True
        )
        
        content = response["choices"][0]["message"]["content"]
        from ..multi_agent import _safe_parse_json
        return _safe_parse_json(content)

    def pause_run(self, run_id: str):
        if run_id in self.runs:
            self.runs[run_id]["status"] = "paused"

    def stop_run(self, run_id: str):
        if run_id in self.runs:
            self.runs[run_id]["status"] = "stopped"

    def list_runs(self) -> List[Dict[str, Any]]:
        # Merges active runs with checkpoints
        checkpoints = self.checkpoint_manager.list_checkpoints()
        results = []
        for rid in checkpoints:
            cp = self.checkpoint_manager.load_checkpoint(rid)
            if cp:
                results.append(cp)
        return results
