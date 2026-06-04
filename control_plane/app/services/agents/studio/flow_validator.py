# Owner: agent-platform
import logging
from typing import Dict, List

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
        edges = graph.get("edges", [])
        
        # 1. Basic integrity
        if not nodes:
            errors.append({"code": "empty_graph", "message": "Flow has no nodes"})
            return errors

        # 2. DAG Validation: Cycle Detection
        if self._has_cycles(nodes, edges):
            errors.append({"code": "cyclic_graph", "message": "Flow graph contains cycles, which are not allowed in this runtime."})

        # 3. Mandatory nodes: must have at least one entry and one final response
        node_types = [n.get("node_type") for n in nodes]
        if "final_response" not in node_types and "handoff" not in node_types:
             errors.append({"code": "missing_terminal_node", "message": "Flow must end with a final_response or handoff node."})

        # 4. Security: Check for high-risk nodes without approval
        for node in nodes:
            if node.get("node_type") == "tool_call":
                config = node.get("config", {})
                if config.get("requires_approval") is False and self._is_high_risk(config.get("tool_name")):
                    errors.append({
                        "code": "missing_approval", 
                        "message": f"High-risk tool '{config.get('tool_name')}' requires explicit approval node or flag."
                    })
                    
        return errors

    def _has_cycles(self, nodes: List[Dict], edges: List[Dict]) -> bool:
        adj = {str(n["id"]): [] for n in nodes}
        for e in edges:
            if str(e["source"]) in adj:
                adj[str(e["source"])].append(str(e["target"]))
        
        visited = set()
        rec_stack = set()
        
        def is_cyclic_util(v):
            visited.add(v)
            rec_stack.add(v)
            for neighbor in adj.get(v, []):
                if neighbor not in visited:
                    if is_cyclic_util(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.remove(v)
            return False
            
        for node in nodes:
            node_id = str(node["id"])
            if node_id not in visited:
                if is_cyclic_util(node_id):
                    return True
        return False

    def _is_high_risk(self, tool_name: str) -> bool:
        high_risk_tools = ["delete_database", "execute_shell", "access_secrets"]
        return tool_name in high_risk_tools
