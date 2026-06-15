# Owner: platform-operations
import uuid
from typing import Any

from app.compat.langgraph.adapters import CompiledStateGraph, StateGraph
from app.models.agents.agent_workflows import (
    AgentWorkflowDefinition,
    AgentWorkflowEdge,
    AgentWorkflowNode,
)
from sqlalchemy.ext.asyncio import AsyncSession


async def convert_langgraph_to_workflow(
    db: AsyncSession,
    tenant_id: str,
    name: str,
    version: str,
    graph: Any,
    description: str | None = None,
) -> AgentWorkflowDefinition:
    """
    Converts a LangGraph StateGraph (or CompiledStateGraph) into a native AgentWorkflowDefinition,
    storing it and its nodes/edges in the database.
    """
    if (
        isinstance(graph, CompiledStateGraph)
        or hasattr(graph, "graph")
        and isinstance(graph.graph, StateGraph)
    ):
        graph = graph.graph

    workflow_def = AgentWorkflowDefinition(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name=name,
        version=version,
        description=description,
        is_active=True,
        input_schema={},
        output_schema={},
        metadata_json={
            "source": "langgraph",
            "entry_point": graph.entry_point,
            "finish_point": graph.finish_point,
        },
    )

    # Add nodes to relationship collection to avoid lazy load reconciliation
    for node_name, node_fn in graph.nodes.items():
        node = AgentWorkflowNode(
            id=uuid.uuid4(),
            node_key=node_name,
            node_type="task",
            config={"callable_name": getattr(node_fn, "__name__", str(node_fn))},
            metadata_json={},
        )
        workflow_def.nodes.append(node)

    # Add edges to relationship collection
    for from_node, to_node in graph.edges:
        edge = AgentWorkflowEdge(
            id=uuid.uuid4(),
            from_node_key=from_node,
            to_node_key=to_node,
            condition_expression=None,
            metadata_json={},
        )
        workflow_def.edges.append(edge)

    db.add(workflow_def)
    await db.flush()
    return workflow_def
