import asyncio
from collections.abc import Callable
from typing import Any

from ..base import BaseAdapter


class StateGraph(BaseAdapter):
    def __init__(self, state_schema: Any):
        self.state_schema = state_schema
        self.nodes: dict[str, Callable] = {}
        self.edges: list[tuple[str, str]] = []
        self.conditional_edges: list[tuple[str, Callable, dict[str, str]]] = []
        self.entry_point: str | None = None
        self.finish_point: str | None = None

    def add_node(self, name: str, action: Callable) -> "StateGraph":
        self.nodes[name] = action
        return self

    def add_edge(self, from_node: str, to_node: str) -> "StateGraph":
        self.edges.append((from_node, to_node))
        return self

    def add_conditional_edges(
        self,
        from_node: str,
        condition: Callable,
        mapping: dict[str, str],
    ) -> "StateGraph":
        self.conditional_edges.append((from_node, condition, mapping))
        return self

    def set_entry_point(self, name: str) -> "StateGraph":
        self.entry_point = name
        return self

    def set_finish_point(self, name: str) -> "StateGraph":
        self.finish_point = name
        return self

    def compile(self) -> "CompiledStateGraph":
        return CompiledStateGraph(self)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_point": self.entry_point,
            "finish_point": self.finish_point,
            "nodes": list(self.nodes.keys()),
            "edges": [(f, t) for f, t in self.edges],
            "conditional_edges": [
                (f, c.__name__ if hasattr(c, "__name__") else str(c), m)
                for f, c, m in self.conditional_edges
            ],
        }


class CompiledStateGraph(BaseAdapter):
    def __init__(self, graph: StateGraph):
        self.graph = graph

    async def invoke(self, state: dict[str, Any]) -> dict[str, Any]:
        current_node = self.graph.entry_point
        current_state = dict(state)
        visited: set[str] = set()

        while current_node:
            if current_node in visited:
                break
            visited.add(current_node)

            node_fn = self.graph.nodes.get(current_node)
            if node_fn:
                if asyncio.iscoroutinefunction(node_fn):
                    res = await node_fn(current_state)
                else:
                    res = node_fn(current_state)
                if isinstance(res, dict):
                    current_state.update(res)

            if current_node == self.graph.finish_point:
                break

            next_node: str | None = None
            for from_n, to_n in self.graph.edges:
                if from_n == current_node:
                    next_node = to_n
                    break

            if next_node is None:
                for from_n, condition, mapping in self.graph.conditional_edges:
                    if from_n == current_node:
                        cond_result = condition(current_state)
                        next_node = mapping.get(cond_result)
                        break

            current_node = next_node

        return current_state

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "CompiledStateGraph",
            "graph": self.graph.to_dict(),
        }
