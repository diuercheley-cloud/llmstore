import logging
from typing import Any, Dict, List, Optional
from app.models.agent_studio import AgentFlowVersion

logger = logging.getLogger(__name__)

class FlowValidator:
    """
    Validates a flow graph for correctness and security policies.
    """
    def validate(self, version: AgentFlowVersion) -> List[Dict[str, str]]:
        errors = []
        graph = version.graph_json
        nodes = graph.get("nodes", [])
        
        # 1. Check for basic node integrity
        if not nodes:
            errors.append({"code": "empty_graph", "message": "Flow has no nodes"})

        # 2. Check for unreachable nodes
        # (Simplified for prototype)
        
        # 3. Security: Check for high-risk nodes without approval
        for node in nodes:
            if node.get("node_type") == "tool_call":
                config = node.get("config", {})
                if config.get("requires_approval") is False and self._is_high_risk(config.get("tool_name")):
                    errors.append({
                        "code": "missing_approval", 
                        "message": f"High-risk tool '{config.get('tool_name')}' requires explicit approval node or flag."
                    })
                    
        return errors

    def _is_high_risk(self, tool_name: str) -> bool:
        high_risk_tools = ["delete_database", "execute_shell", "access_secrets"]
        return tool_name in high_risk_tools
