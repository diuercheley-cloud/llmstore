from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from app.core.time import utc_now
from app.services.agents.agent_graph.engine import AgentGraphEngine
from app.services.agents.agent_graph.models import (
    AgentGraphSpec,
    AgentNode,
    AgentNodeType,
    GraphEdge,
    GraphExecutionResult,
)
from app.services.agents.simulation import SimulationRuntime
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class AgentGraphDryRunRunner:
    """
    Executes an Agent Studio graph version in a controlled environment.
    Ensures no side effects occur while collecting real execution trace data.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.engine = AgentGraphEngine(node_runner=self._node_runner)
        self.simulation = SimulationRuntime()

    async def run_dry_run(
        self, graph_json: dict[str, Any], global_input: dict[str, Any] = None
    ) -> dict[str, Any]:
        """
        Runs the graph spec in simulation mode.
        """
        spec = self._to_spec(graph_json)
        run_id = f"dry-run-{uuid.uuid4()}"

        logger.info(f"Starting real dry-run for graph with run_id {run_id}")

        result = await self.engine.execute(spec, run_id=run_id, global_input=global_input)

        return self._format_response(result)

    async def _node_runner(self, node: AgentNode, context: dict[str, Any]) -> dict[str, Any]:
        """
        Specialized node runner for dry-run (SimulationMode).
        """
        node_id = node.id
        # The original config from Studio node is stored in node.config
        ntype = node.config.get("node_type", "unknown")
        global_input = context.get("global_input") or {}

        events = []
        events.append({"event": "node_started", "timestamp": utc_now().isoformat()})

        start_time = time.perf_counter()
        output = {}
        warnings = []
        status = "completed"

        try:
            if ntype in ("agent", "llm_call", "model_reasoning"):
                # Simulate reasoning
                # In a more advanced version, we could call the real LLM with a dry-run prompt
                # or use a MockAgentLLMProvider.
                output = {
                    "content": f"Simulated reasoning for node {node_id}",
                    "confidence": 0.95,
                    "model": node.config.get("config", {}).get("model", "gpt-4-sim"),
                }
                events.append({"event": "reasoning_simulated", "node_id": node_id})

            elif ntype == "tool_call":
                tool_name = node.config.get("config", {}).get("tool_name", "unknown_tool")
                tool_params = node.config.get("config", {}).get("parameters", {})

                events.append({"event": "tool_call_requested", "tool": tool_name})

                # Use SimulationRuntime to safely mock behavior
                category = self.simulation.classify_tool(tool_name)
                output = self.simulation.simulate_tool_execution(tool_name, category, tool_params)

                events.append(
                    {"event": "tool_call_simulated", "tool": tool_name, "category": category}
                )

            elif ntype == "memory_read":
                key = node.config.get("config", {}).get("key", "default_key")
                events.append({"event": "memory_read", "key": key})
                output = {"data": f"Simulated memory value for '{key}'"}

            elif ntype == "memory_write":
                key = node.config.get("config", {}).get("key", "default_key")
                events.append({"event": "memory_write_blocked", "key": key})
                warnings.append(f"Memory write to '{key}' was blocked during dry-run.")
                output = {"status": "blocked", "key": key}

            elif ntype == "condition":
                # Simple simulation: take the first branch or default
                output = {"branch": "default", "decision_simulated": True}
                events.append({"event": "logic_gate_simulated", "decision": "default"})

            elif ntype == "final_response":
                output = {"response": "Simulated final response"}
                events.append({"event": "final_response_reached"})

            else:
                output = {"message": f"Node type '{ntype}' execution simulated."}
                events.append({"event": "generic_node_simulated", "type": ntype})

            events.append({"event": "node_completed", "timestamp": utc_now().isoformat()})

        except Exception as e:
            logger.exception(f"Error in dry-run node {node_id}")
            status = "failed"
            output = {"error": str(e)}
            events.append(
                {"event": "node_failed", "error": str(e), "timestamp": utc_now().isoformat()}
            )

        duration_ms = (time.perf_counter() - start_time) * 1000

        # This payload will be stored in NodeExecutionResult.output
        return {
            "node_id": node_id,
            "type": ntype,
            "status": status,
            "input": node.config.get("config", {}),
            "output": output,
            "duration_ms": duration_ms,
            "events": events,
            "warnings": warnings,
            "diff_state": {"state_change": "none (simulated)"},
        }

    def _to_spec(self, graph_json: dict[str, Any]) -> AgentGraphSpec:
        nodes = []
        for n in graph_json.get("nodes", []):
            nodes.append(
                AgentNode(
                    id=str(n["id"]),
                    type=AgentNodeType.WORKER,  # Fixed type for engine, real type in config
                    config=n,
                    max_retries=0,  # No retries in dry-run
                )
            )

        edges = []
        for e in graph_json.get("edges", []):
            edges.append(GraphEdge(source=str(e["source"]), target=str(e["target"])))

        return AgentGraphSpec(nodes=nodes, edges=edges)

    def _format_response(self, result: GraphExecutionResult) -> dict[str, Any]:
        trace = []
        side_effects = []

        # Sort node results by completion time if available, or topological order
        # For simplicity, we just use the order they were recorded in the result
        for nr in result.node_results.values():
            trace.append(nr.output)
            if nr.output.get("type") in ("tool_call", "memory_write"):
                side_effects.append(nr.node_id)

        return {
            "status": result.status.value,
            "trace": trace,
            "final_output": {"dry_run": True, "result": result.status.value},
            "side_effects_prevented": side_effects,
        }
