# Owner: agent-platform
import yaml
import logging
import os
from typing import Dict, Any, Optional
from app.core.config import get_settings
from app.models.agents import AgentDefinition, AgentRun

logger = logging.getLogger(__name__)

class AgentBudgetService:
    _config: Optional[Dict[str, Any]] = None

    def __init__(self):
        self.settings = get_settings()
        if AgentBudgetService._config is None:
            self._load_config()

    def _load_config(self):
        config_path = os.path.join("config", "agent-slo-classes.yaml")
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                AgentBudgetService._config = yaml.safe_load(f)
        else:
            logger.warning(f"Budget config not found at {config_path}, using empty defaults")
            AgentBudgetService._config = {"classes": {}}

    def get_class_config(self, agent_class: Optional[str]) -> Dict[str, Any]:
        classes = AgentBudgetService._config.get("classes", {})
        if not agent_class or agent_class not in classes:
            return classes.get("default", {})
        return classes[agent_class]

    async def validate_run_budget(self, agent_def: AgentDefinition, run: AgentRun) -> tuple[bool, Optional[str]]:
        """
        Validates if the current run is within the budgets defined for its class.
        Returns (is_valid, reason).
        """
        cls_cfg = self.get_class_config(agent_def.agent_class)
        if not cls_cfg:
            return True, None

        # 1. Cost Budget
        max_cost = cls_cfg.get("max_cost_brl_per_run")
        if max_cost and run.estimated_cost_brl > max_cost:
            return False, f"Cost budget exceeded: {run.estimated_cost_brl:.4f} > {max_cost} BRL"

        # 2. Token Budget
        max_tokens = cls_cfg.get("max_tokens_per_run")
        if max_tokens and run.total_tokens > max_tokens:
            return False, f"Token budget exceeded: {run.total_tokens} > {max_tokens} tokens"

        # 3. Steps Budget
        max_steps = cls_cfg.get("max_steps")
        if max_steps and run.total_steps > max_steps:
            return False, f"Max steps exceeded: {run.total_steps} > {max_steps} steps"

        # 4. Tool Calls Budget
        max_tools = cls_cfg.get("max_tool_calls")
        if max_tools and (getattr(run, 'tool_calls_count', 0) or 0) > max_tools:
            return False, f"Tool calls budget exceeded: {run.tool_calls_count} > {max_tools}"

        # 5. Memory Reads Budget
        max_mem = cls_cfg.get("max_memory_reads")
        if max_mem and (getattr(run, 'memory_reads_count', 0) or 0) > max_mem:
            return False, f"Memory reads budget exceeded: {run.memory_reads_count} > {max_mem}"

        # 6. Replans Budget
        max_replans = cls_cfg.get("max_replans")
        if max_replans and (getattr(run, 'replans_count', 0) or 0) > max_replans:
            return False, f"Replans budget exceeded: {run.replans_count} > {max_replans}"

        # 7. Approval Wait Time Budget
        max_wait = cls_cfg.get("max_approval_wait_seconds")
        if max_wait and (getattr(run, 'approval_wait_seconds', 0) or 0) > max_wait:
            return False, f"Approval wait time exceeded: {run.approval_wait_seconds} > {max_wait}s"

        return True, None

    def get_operational_limits(self, agent_class: Optional[str]) -> Dict[str, Any]:
        return self.get_class_config(agent_class)
