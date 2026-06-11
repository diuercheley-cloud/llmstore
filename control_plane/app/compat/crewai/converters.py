# Owner: platform-operations
import uuid
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.agents.agents import AgentDefinition
from app.models.agents.agent_workflows import AgentWorkflowDefinition, AgentWorkflowNode, AgentWorkflowEdge
from app.compat.crewai.adapters import Agent, Task, Crew

async def convert_crew_agent_to_agent_definition(
    db: AsyncSession,
    tenant_id: str,
    agent: Agent,
    owner: str = "crewai-migrated"
) -> AgentDefinition:
    """
    Converts a CrewAI Agent to a native AgentDefinition.
    """
    agent_def = AgentDefinition(
        id=uuid.uuid4(),
        name=agent.role,
        version="1.0.0",
        description=f"Migrated CrewAI Agent - Goal: {agent.goal}",
        instructions=f"Role: {agent.role}\nGoal: {agent.goal}\nBackstory: {agent.backstory}",
        model_id=str(agent.llm),
        owner=owner,
        tenant_id=tenant_id,
        status="active",
        allowed_tools=[str(tool) for tool in agent.tools] if agent.tools else None
    )
    db.add(agent_def)
    await db.flush()
    return agent_def

async def convert_crew_to_workflow(
    db: AsyncSession,
    tenant_id: str,
    name: str,
    version: str,
    crew: Crew,
    description: str | None = None
) -> AgentWorkflowDefinition:
    """
    Converts a CrewAI Crew (and its tasks) into a native AgentWorkflowDefinition.
    The tasks are chained sequentially in the order of definition.
    """
    workflow_def = AgentWorkflowDefinition(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name=name,
        version=version,
        description=description or "Migrated CrewAI Crew workflow",
        is_active=True,
        input_schema={},
        output_schema={},
        metadata_json={"source": "crewai"}
    )
    
    # Store agents in DB and map role -> agent definition ID
    agent_map = {}
    for agent in crew.agents:
        agent_def = await convert_crew_agent_to_agent_definition(db, tenant_id, agent)
        agent_map[agent.role] = agent_def.id
        
    node_keys = []
    
    # Add a node for each task
    for idx, task in enumerate(crew.tasks):
        node_key = f"task_{idx}_{task.id.hex[:8]}"
        node_keys.append(node_key)
        
        assigned_agent = task.agent or (crew.agents[0] if crew.agents else None)
        assigned_agent_id = str(agent_map[assigned_agent.role]) if assigned_agent else None
        
        node = AgentWorkflowNode(
            id=uuid.uuid4(),
            node_key=node_key,
            node_type="task",
            config={
                "description": task.description,
                "expected_output": task.expected_output,
                "assigned_agent_id": assigned_agent_id,
                "tools": [str(t) for t in task.tools]
            },
            metadata_json={}
        )
        workflow_def.nodes.append(node)
        
    # Chain tasks sequentially
    for idx in range(len(node_keys) - 1):
        edge = AgentWorkflowEdge(
            id=uuid.uuid4(),
            from_node_key=node_keys[idx],
            to_node_key=node_keys[idx + 1],
            condition_expression=None,
            metadata_json={}
        )
        workflow_def.edges.append(edge)
        
    db.add(workflow_def)
    await db.flush()
    return workflow_def
