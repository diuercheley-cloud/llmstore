# Owner: agent-platform
import logging
from typing import Dict, List

import networkx as nx
from app.models.agent_workflows import AgentWorkflowDefinition

logger = logging.getLogger(__name__)

class WorkflowDAG:
    """
    Handles DAG validation and traversal for agent workflows.
    Uses networkx for graph algorithms.
    """
    
    def __init__(self, definition: AgentWorkflowDefinition):
        self.definition = definition
        self.graph = nx.DiGraph()
        self._build_graph()

    def _build_graph(self):
        for node in self.definition.nodes:
            self.graph.add_node(node.node_key, type=node.node_type, config=node.config)
        
        for edge in self.definition.edges:
            self.graph.add_edge(edge.from_node_key, edge.to_node_key, condition=edge.condition_expression)

    def validate(self) -> List[str]:
        """
        Validates the DAG:
        - Must be a DAG (no cycles)
        - Must have at least one node
        - Must have a 'start' node (or nodes with no incoming edges)
        - Must have nodes with no outgoing edges (leaf nodes)
        """
        errors = []
        if not self.definition.nodes:
            errors.append("Workflow must have at least one node.")
            return errors

        if not nx.is_directed_acyclic_graph(self.graph):
            errors.append("Workflow contains cycles and is not a valid DAG.")

        start_nodes = [n for n, d in self.graph.in_degree() if d == 0]
        if not start_nodes:
            errors.append("Workflow must have at least one start node (no incoming edges).")
        
        # Optionally enforce a node named 'start'
        # if 'start' not in self.graph.nodes:
        #     errors.append("Workflow must have a node named 'start'.")

        return errors

    def get_next_nodes(self, completed_node_key: str, context: Dict) -> List[str]:
        """
        Returns the next nodes to execute based on a completed node and context.
        Handles conditional branching.
        """
        successors = list(self.graph.successors(completed_node_key))
        if not successors:
            return []

        # If it's a condition node, we evaluate conditions on edges
        node_data = self.graph.nodes[completed_node_key]
        if node_data['type'] == 'condition':
            return self._evaluate_conditions(completed_node_key, context)
        
        # For other nodes, we might have multiple successors (implicit fan-out)
        # unless it's a parallel_fanout node which explicitly handles this.
        return successors

    def _evaluate_conditions(self, node_key: str, context: Dict) -> List[str]:
        """
        Evaluates condition expressions on outgoing edges.
        Returns the first matching branch (or all matching? Usually first for if/else).
        """
        next_nodes = []
        edges = [e for e in self.definition.edges if e.from_node_key == node_key]
        
        for edge in edges:
            if not edge.condition_expression:
                # Default branch if no condition
                next_nodes.append(edge.to_node_key)
                continue
            
            if self._check_condition(edge.condition_expression, context):
                next_nodes.append(edge.to_node_key)
                # Typically if/else means we stop at first match
                break
        
        return next_nodes

    def _check_condition(self, expression: str, context: Dict) -> bool:
        """
        Evaluates a simple condition expression against the context.
        Supports policy results, tool results, memory values, etc.
        """
        # Simplistic evaluation for now. In a real system, use a safe eval or a DSL.
        # context might look like: {"results": {"task1": {"score": 0.9}}, "memory": {"user_id": 123}}
        try:
            # Safe-ish eval with restricted globals
            return eval(expression, {"__builtins__": {}}, context) # nosec
        except Exception as e:
            logger.error(f"Error evaluating condition '{expression}': {e}")
            return False

    def get_dependencies(self, node_key: str) -> List[str]:
        """Returns nodes that must complete before this node can start."""
        return list(self.graph.predecessors(node_key))

    def is_fanin_join(self, node_key: str) -> bool:
        return self.graph.nodes[node_key].get('type') == 'fanin_join'
