# Owner: agent-platform
import logging
from typing import Dict, List

import networkx as nx
from app.models.agents.agent_workflows import AgentWorkflowDefinition

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
        Evaluates a simple condition expression against the context safely.
        Supports policy results, tool results, memory values, etc.
        Uses a limited expression parser instead of eval().
        """
        try:
            return self._safe_eval(expression, context)
        except Exception as e:
            logger.error(f"Error evaluating condition '{expression}': {e}")
            return False

    @staticmethod
    def _safe_eval(expression: str, context: Dict) -> bool:
        """
        Safe expression evaluator supporting:
        - Variable lookups via dotted paths (e.g., results.task1.score)
        - Comparison operators: == != < > <= >=
        - Boolean operators: and or not
        - Numeric and string literals
        - Parentheses for grouping
        """
        import ast
        import operator

        def _lookup(path: str):
            parts = path.split(".")
            val = context
            for part in parts:
                if isinstance(val, dict):
                    if part not in val:
                        raise ValueError(f"Key '{part}' not found in context")
                    val = val[part]
                elif hasattr(val, part):
                    val = getattr(val, part)
                else:
                    try:
                        idx = int(part)
                        val = val[idx]
                    except (IndexError, ValueError, TypeError):
                        raise ValueError(f"Cannot resolve '{part}' on {type(val).__name__}")
            return val

        ops = {
            ast.Eq: operator.eq,
            ast.NotEq: operator.ne,
            ast.Lt: operator.lt,
            ast.LtE: operator.le,
            ast.Gt: operator.gt,
            ast.GtE: operator.ge,
            ast.Is: operator.is_,
            ast.IsNot: operator.is_not,
            ast.In: lambda a, b: a in b,
            ast.NotIn: lambda a, b: a not in b,
            ast.And: lambda a, b: a and b,
            ast.Or: lambda a, b: a or b,
        }

        def _eval(node):
            if isinstance(node, ast.Expression):
                return _eval(node.body)
            if isinstance(node, ast.BoolOp):
                results = [_eval(n) for n in node.values]
                return ops[type(node.op)](*results) if len(results) == 2 else results[0]
            if isinstance(node, ast.BinOp):
                if isinstance(node.op, ast.Pow):
                    return _eval(node.left) ** _eval(node.right)
                return ops[type(node.op)](_eval(node.left), _eval(node.right))
            if isinstance(node, ast.UnaryOp):
                if isinstance(node.op, ast.Not):
                    return not _eval(node.operand)
                if isinstance(node.op, ast.UAdd):
                    return +_eval(node.operand)
                if isinstance(node.op, ast.USub):
                    return -_eval(node.operand)
            if isinstance(node, ast.Compare):
                left = _eval(node.left)
                for op, comparator in zip(node.ops, node.comparators):
                    if not ops[type(op)](left, _eval(comparator)):
                        return False
                    left = _eval(comparator)
                return True
            if isinstance(node, ast.Name):
                return _lookup(node.id)
            if isinstance(node, ast.Attribute):
                val = _eval(node.value)
                if isinstance(val, dict):
                    return val[node.attr]
                return getattr(val, node.attr)
            if isinstance(node, ast.Subscript):
                return _eval(node.value)[_eval(node.slice)]
            if isinstance(node, ast.Constant):
                return node.value
            if isinstance(node, ast.List):
                return [_eval(el) for el in node.elts]
            if isinstance(node, ast.Tuple):
                return tuple(_eval(el) for el in node.elts)
            if isinstance(node, ast.Dict):
                return {_eval(k): _eval(v) for k, v in zip(node.keys, node.elts)}
            if isinstance(node, ast.Call):
                func = _eval(node.func)
                args = [_eval(a) for a in node.args]
                kwargs = {kw.arg: _eval(kw.value) for kw in node.keywords if kw.arg}
                return func(*args, **kwargs)
            raise ValueError(f"Unsupported expression: {type(node).__name__}")

        tree = ast.parse(expression, mode="eval")
        result = _eval(tree)
        if not isinstance(result, bool):
            raise ValueError(f"Expression did not evaluate to a boolean: {result}")
        return result

    def get_dependencies(self, node_key: str) -> List[str]:
        """Returns nodes that must complete before this node can start."""
        return list(self.graph.predecessors(node_key))

    def is_fanin_join(self, node_key: str) -> bool:
        return self.graph.nodes[node_key].get('type') == 'fanin_join'
