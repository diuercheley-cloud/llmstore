# Owner: platform-operations
import asyncio
from collections.abc import Callable
from typing import Any


class StateGraph:
    """
    Compatibility Adapter for LangGraph StateGraph.
    Allows developers to define LangGraph nodes and edges, compiling into a runnable.
    """

    def __init__(self, state_schema: Any):
        self.state_schema = state_schema
        self.nodes = {}
        self.edges = []
        self.entry_point = None
        self.finish_point = None

    def add_node(self, name: str, action: Callable):
        self.nodes[name] = action

    def add_edge(self, from_node: str, to_node: str):
        self.edges.append((from_node, to_node))

    def set_entry_point(self, name: str):
        self.entry_point = name

    def set_finish_point(self, name: str):
        self.finish_point = name

    def compile(self) -> "CompiledStateGraph":
        return CompiledStateGraph(self)


class CompiledStateGraph:
    def __init__(self, graph: StateGraph):
        self.graph = graph

    async def invoke(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Executes the nodes sequentially or according to edges.
        """
        current_node = self.graph.entry_point
        current_state = dict(state)

        visited = set()

        while current_node and current_node != self.graph.finish_point:
            if current_node in visited:
                # Avoid infinite loops in simple mock execution
                break
            visited.add(current_node)

            # Execute node callable
            node_fn = self.graph.nodes.get(current_node)
            if node_fn:
                if asyncio.iscoroutinefunction(node_fn):
                    res = await node_fn(current_state)
                else:
                    res = node_fn(current_state)
                if isinstance(res, dict):
                    current_state.update(res)

            # Find next node
            next_node = None
            for from_n, to_n in self.graph.edges:
                if from_n == current_node:
                    next_node = to_n
                    break

            current_node = next_node

        return current_state
