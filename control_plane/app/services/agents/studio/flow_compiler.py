# Owner: agent-platform
import logging
import uuid
from typing import Any

from app.models.agents.agent_studio import AgentFlowVersion

logger = logging.getLogger(__name__)


class FlowCompiler:
    """
    Compiles a visual flow graph into an executable AgentPlan or Workflow.
    """

    def compile(self, version: AgentFlowVersion) -> dict[str, Any]:
        graph = version.graph_json
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])

        logger.info(f"Compiling flow version {version.id} with {len(nodes)} nodes")

        # 1. Topological Sort for dependencies
        sorted_nodes = self._topological_sort(nodes, edges)

        # 2. Build tasks
        tasks = []
        node_to_task_id = {}

        for node in sorted_nodes:
            task_id = str(uuid.uuid4())
            node_to_task_id[str(node["id"])] = task_id

            dependencies = []
            for edge in edges:
                if str(edge["target"]) == str(node["id"]):
                    parent_task_id = node_to_task_id.get(str(edge["source"]))
                    if parent_task_id:
                        dependencies.append(parent_task_id)

            tasks.append(
                {
                    "id": task_id,
                    "node_id": str(node["id"]),
                    "title": node.get("label") or node.get("node_type"),
                    "task_type": self._map_node_type(node.get("node_type")),
                    "input_data": node.get("config", {}),
                    "dependencies": dependencies,
                }
            )

        return {"flow_id": str(version.flow_id), "version_id": str(version.id), "tasks": tasks}

    def _topological_sort(self, nodes: list[dict], edges: list[dict]) -> list[dict]:
        # Kanh's algorithm for topological sort
        in_degree = {str(n["id"]): 0 for n in nodes}
        adj = {str(n["id"]): [] for n in nodes}

        for e in edges:
            u, v = str(e["source"]), str(e["target"])
            if u in adj and v in adj:
                adj[u].append(v)
                in_degree[v] += 1

        queue = [str(n["id"]) for n in nodes if in_degree[str(n["id"])] == 0]
        sorted_ids = []

        while queue:
            u = queue.pop(0)
            sorted_ids.append(u)
            for v in adj[u]:
                in_degree[v] -= 1
                if in_degree[v] == 0:
                    queue.append(v)

        id_to_node = {str(n["id"]): n for n in nodes}
        return [id_to_node[nid] for sorted_id in sorted_ids if (nid := sorted_id) in id_to_node]

    def _map_node_type(self, node_type: str) -> str:
        mapping = {
            "agent": "model_reasoning",
            "llm_call": "model_reasoning",
            "tool_call": "tool_call",
            "memory_read": "memory_read",
            "approval": "approval",
            "condition": "logic_gate",
            "handoff": "handoff",
            "final_response": "final_response",
        }
        return mapping.get(node_type, "generic")
