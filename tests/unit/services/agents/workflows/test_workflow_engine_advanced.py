# Owner: agent-platform
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.models.agents.agent_workflows import (
    AgentWorkflowDefinition,
    AgentWorkflowEdge,
    AgentWorkflowNode,
    AgentWorkflowRun,
)
from app.services.agents.workflows.workflow_dag import WorkflowDAG
from app.services.agents.workflows.workflow_engine import WorkflowEngine
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def mock_db():
    return MagicMock(spec=AsyncSession)

@pytest.fixture
def workflow_engine(mock_db):
    return WorkflowEngine(mock_db)

@pytest.mark.asyncio
async def test_dag_validation():
    # Test valid DAG
    nodes = [
        AgentWorkflowNode(node_key="start", node_type="task"),
        AgentWorkflowNode(node_key="end", node_type="task")
    ]
    edges = [AgentWorkflowEdge(from_node_key="start", to_node_key="end")]
    definition = AgentWorkflowDefinition(nodes=nodes, edges=edges)
    
    dag = WorkflowDAG(definition)
    errors = dag.validate()
    assert len(errors) == 0

    # Test cycle
    edges.append(AgentWorkflowEdge(from_node_key="end", to_node_key="start"))
    definition = AgentWorkflowDefinition(nodes=nodes, edges=edges)
    dag = WorkflowDAG(definition)
    errors = dag.validate()
    assert "Workflow contains cycles and is not a valid DAG." in errors

@pytest.mark.asyncio
async def test_branching_if_else(workflow_engine, mock_db):
    # Setup a definition with a condition node
    nodes = [
        AgentWorkflowNode(node_key="start", node_type="task"),
        AgentWorkflowNode(node_key="check", node_type="condition", config={
            "branches": [
                {"condition": {"type": "memory_value", "target": "score", "operator": "gt", "value": 10}, "target": "path_a"},
                {"condition": None, "target": "path_b"}
            ]
        }),
        AgentWorkflowNode(node_key="path_a", node_type="task"),
        AgentWorkflowNode(node_key="path_b", node_type="task")
    ]
    edges = [
        AgentWorkflowEdge(from_node_key="start", to_node_key="check"),
        AgentWorkflowEdge(from_node_key="check", to_node_key="path_a"),
        AgentWorkflowEdge(from_node_key="check", to_node_key="path_b")
    ]
    definition = AgentWorkflowDefinition(id=uuid.uuid4(), nodes=nodes, edges=edges)
    
    run = AgentWorkflowRun(
        workflow_definition_id=definition.id,
        current_state="processing",
        context={"memory": {"score": 15}},
        state_data={"active_nodes": ["check"], "completed_nodes": []}
    )
    
    mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: definition))
    sm = MagicMock()
    sm.get_context.return_value = run.context
    sm.transition_to = AsyncMock()
    
    await workflow_engine._execute_dag_logic(run, sm)
    
    # Check that path_a was selected
    sm.update_state_data.assert_called()
    args, _ = sm.update_state_data.call_args
    state_data = args[0]
    assert "path_a" in state_data["active_nodes"]
    assert "path_b" not in state_data["active_nodes"]

@pytest.mark.asyncio
async def test_parallel_fanout_fanin(workflow_engine, mock_db):
    # Setup fan-out/fan-in
    nodes = [
        AgentWorkflowNode(node_key="fanout", node_type="parallel_fanout", config={}),
        AgentWorkflowNode(node_key="branch_1", node_type="task", config={}),
        AgentWorkflowNode(node_key="branch_2", node_type="task", config={}),
        AgentWorkflowNode(node_key="join", node_type="fanin_join", config={})
    ]
    edges = [
        AgentWorkflowEdge(from_node_key="fanout", to_node_key="branch_1"),
        AgentWorkflowEdge(from_node_key="fanout", to_node_key="branch_2"),
        AgentWorkflowEdge(from_node_key="branch_1", to_node_key="join"),
        AgentWorkflowEdge(from_node_key="branch_2", to_node_key="join")
    ]
    definition = AgentWorkflowDefinition(id=uuid.uuid4(), nodes=nodes, edges=edges)
    
    run = AgentWorkflowRun(
        workflow_definition_id=definition.id,
        current_state="processing",
        state_data={"active_nodes": ["fanout"], "completed_nodes": []}
    )
    
    mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: definition))
    sm = MagicMock()
    sm.get_context.return_value = {}
    sm.transition_to = AsyncMock()

    # 1. Execute Fan-out
    await workflow_engine._execute_dag_logic(run, sm)
    args, _ = sm.update_state_data.call_args
    state_data = args[0]
    assert "branch_1" in state_data["active_nodes"]
    assert "branch_2" in state_data["active_nodes"]

    # 2. Execute one branch
    run.state_data = {"active_nodes": ["branch_1"], "completed_nodes": ["fanout"]}
    await workflow_engine._execute_dag_logic(run, sm)
    args, _ = sm.update_state_data.call_args
    state_data = args[0]
    assert "join" in state_data["active_nodes"] # Should be active but not ready if join checks predecessors
    
    # In my implementation, join node stays active until ready
    assert "join" in state_data["active_nodes"]

@pytest.mark.asyncio
async def test_subworkflow_execution(workflow_engine, mock_db):
    sub_def_id = uuid.uuid4()
    nodes = [
        AgentWorkflowNode(node_key="sub", node_type="subworkflow", config={"subworkflow_definition_id": str(sub_def_id)})
    ]
    definition = AgentWorkflowDefinition(id=uuid.uuid4(), nodes=nodes, edges=[])
    
    run = AgentWorkflowRun(
        workflow_definition_id=definition.id,
        current_state="start",
        state_data={"active_nodes": ["sub"]}
    )
    
    mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: definition))
    sm = MagicMock()
    sm.get_context.return_value = {}
    sm.transition_to = AsyncMock()

    # Mock SubworkflowRuntime to return not complete first, then complete
    with MagicMock() as mock_runtime:
        mock_runtime.is_subworkflow_complete = AsyncMock(side_effect=[False, True])
        mock_runtime.start_subworkflow = AsyncMock()
        mock_runtime.get_subworkflow_results = AsyncMock(return_value={"result": "ok"})
        
        # We need to mock the instantiation of SubworkflowRuntime
        with pytest.MonkeyPatch().context() as m:
            m.setattr("app.services.agents.workflows.workflow_engine.SubworkflowRuntime", lambda db, run: mock_runtime)
            
            # First call: starts subworkflow
            await workflow_engine._execute_dag_logic(run, sm)
            mock_runtime.start_subworkflow.assert_called()
            
            # Second call: completes subworkflow
            run.state_data = {"active_nodes": ["sub"]}
            await workflow_engine._execute_dag_logic(run, sm)
            sm.update_context.assert_called_with({"subworkflow_sub": {"result": "ok"}})
