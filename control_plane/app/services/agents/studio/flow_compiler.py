import uuid
import logging
from typing import Any, Dict, List, Optional
from app.models.agent_studio import AgentFlowVersion
from app.models.agents import AgentPlan

logger = logging.getLogger(__name__)

class FlowCompiler:
    """
    Compiles a visual flow graph into an executable AgentPlan or Workflow.
    """
    def compile(self, version: AgentFlowVersion) -> Dict[str, Any]:
        graph = version.graph_json
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])
        
        logger.info(f"Compiling flow version {version.id} with {len(nodes)} nodes")
        
        # Simple compilation logic: convert nodes to sequential tasks
        # In a real app, this would perform a topological sort and handle branching
        tasks = []
        for node in nodes:
            tasks.append({
                "id": node.get("id"),
                "title": node.get("label") or node.get("node_type"),
                "task_type": self._map_node_type(node.get("node_type")),
                "input_data": node.get("config", {})
            })
            
        return {
            "flow_id": str(version.flow_id),
            "version_id": str(version.id),
            "tasks": tasks
        }

    def _map_node_type(self, node_type: str) -> str:
        mapping = {
            "agent": "model_reasoning",
            "tool_call": "tool_call",
            "approval": "approval",
            "condition": "logic_gate",
            "final": "synthesis"
        }
        return mapping.get(node_type, "generic")
