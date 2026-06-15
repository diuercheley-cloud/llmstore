# Owner: platform-operations
import os
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# Force a local writable database file in the workspace
TEST_DB_FILE = Path("test-compat-layer.db").resolve()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_FILE}"

import app.db.session
from app.db.base import Base
from app.db.session import get_db, get_db_session
from app.main import app as main_app

# Create a fresh engine for tests with NullPool to avoid unlinked SQLite descriptor issues
engine = create_async_engine(f"sqlite+aiosqlite:///{TEST_DB_FILE}", poolclass=NullPool)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# Patch the global session and engine
app.db.session.engine = engine
app.db.session.SessionLocal = SessionLocal


async def override_get_db():
    async with SessionLocal() as session:
        yield session


main_app.dependency_overrides[get_db] = override_get_db
main_app.dependency_overrides[get_db_session] = override_get_db


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    # Ensure any stale file is removed before starting the test
    if TEST_DB_FILE.exists():
        try:
            TEST_DB_FILE.unlink()
        except Exception:
            pass

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    if TEST_DB_FILE.exists():
        try:
            TEST_DB_FILE.unlink()
        except Exception:
            pass


@pytest_asyncio.fixture
async def test_session():
    async with SessionLocal() as session:
        yield session


from app.compat.autogen.adapters import ConversableAgent, UserProxyAgent
from app.compat.autogen.converters import (
    convert_autogen_agent_to_agent_definition,
    convert_autogen_chat_to_session,
)
from app.compat.autogen.importers import import_autogen_agent_from_source
from app.compat.crewai.adapters import Agent as CrewAgent
from app.compat.crewai.adapters import Crew
from app.compat.crewai.adapters import Task as CrewTask
from app.compat.crewai.converters import convert_crew_to_workflow
from app.compat.crewai.importers import import_crew_from_source
from app.compat.langgraph.adapters import CompiledStateGraph, StateGraph
from app.compat.langgraph.converters import convert_langgraph_to_workflow
from app.compat.langgraph.importers import import_langgraph_from_source
from app.compat.report import CompatibilityAnalyzer
from app.models.agents.agent_workflows import (
    AgentWorkflowEdge,
    AgentWorkflowNode,
)
from app.models.agents.agents import AgentDefinition


@pytest.mark.asyncio
async def test_langgraph_compat(test_session: AsyncSession):
    # 1. Test Adapter Execution
    def node_a(state):
        state["a"] = 1
        return state

    def node_b(state):
        state["b"] = 2
        return state

    builder = StateGraph(state_schema=dict)
    builder.add_node("node_a", node_a)
    builder.add_node("node_b", node_b)
    builder.add_edge("node_a", "node_b")
    builder.set_entry_point("node_a")
    builder.set_finish_point("node_b")

    graph = builder.compile()
    assert isinstance(graph, CompiledStateGraph)

    result = await graph.invoke({"input": "test"})
    assert result["a"] == 1
    assert result["input"] == "test"

    # 2. Test Converter
    tenant_id = "tenant-lg"
    wf_def = await convert_langgraph_to_workflow(
        db=test_session,
        tenant_id=tenant_id,
        name="LangGraph Workflow",
        version="1.0.0",
        graph=graph,
    )

    assert wf_def.name == "LangGraph Workflow"
    assert wf_def.tenant_id == tenant_id

    # Check nodes in DB
    nodes_res = await test_session.execute(
        select(AgentWorkflowNode).where(AgentWorkflowNode.workflow_definition_id == wf_def.id)
    )
    nodes = nodes_res.scalars().all()
    assert len(nodes) == 2
    node_keys = {n.node_key for n in nodes}
    assert "node_a" in node_keys
    assert "node_b" in node_keys

    # Check edges in DB
    edges_res = await test_session.execute(
        select(AgentWorkflowEdge).where(AgentWorkflowEdge.workflow_definition_id == wf_def.id)
    )
    edges = edges_res.scalars().all()
    assert len(edges) == 1
    assert edges[0].from_node_key == "node_a"
    assert edges[0].to_node_key == "node_b"

    # 3. Test Importer
    source_code = """
builder = StateGraph(state_schema=dict)
builder.add_node("start", lambda x: x)
builder.set_entry_point("start")
graph = builder.compile()
"""
    imported_graph = import_langgraph_from_source(source_code, target_variable="graph")
    assert isinstance(imported_graph, CompiledStateGraph)
    assert "start" in imported_graph.graph.nodes


@pytest.mark.asyncio
async def test_crewai_compat(test_session: AsyncSession):
    # 1. Test Adapter Execution
    agent = CrewAgent(role="Researcher", goal="Find info", backstory="A detailed researcher")
    task = CrewTask(
        description="Search for compat layers", expected_output="a report list", agent=agent
    )
    crew = Crew(agents=[agent], tasks=[task])
    output = crew.kickoff(inputs={"topic": "compat"})

    assert "Simulated output matching target" in output
    assert "Find info" in agent.goal

    # 2. Test Converter
    tenant_id = "tenant-crew"
    wf_def = await convert_crew_to_workflow(
        db=test_session, tenant_id=tenant_id, name="Crew Workflow", version="1.1.0", crew=crew
    )

    assert wf_def.name == "Crew Workflow"

    nodes_res = await test_session.execute(
        select(AgentWorkflowNode).where(AgentWorkflowNode.workflow_definition_id == wf_def.id)
    )
    nodes = nodes_res.scalars().all()
    assert len(nodes) == 1
    assert "Search for compat layers" in nodes[0].config["description"]

    # Check generated AgentDefinition
    agents_res = await test_session.execute(
        select(AgentDefinition).where(AgentDefinition.tenant_id == tenant_id)
    )
    agent_defs = agents_res.scalars().all()
    assert len(agent_defs) == 1
    assert agent_defs[0].name == "Researcher"
    assert "A detailed researcher" in agent_defs[0].instructions

    # 3. Test Importer
    source_code = """
researcher = Agent(role="Writer", goal="write code", backstory="coder")
task = Task(description="write", expected_output="code", agent=researcher)
crew = Crew(agents=[researcher], tasks=[task])
"""
    imported_crew = import_crew_from_source(source_code, target_variable="crew")
    assert isinstance(imported_crew, Crew)
    assert len(imported_crew.agents) == 1
    assert imported_crew.agents[0].role == "Writer"


@pytest.mark.asyncio
async def test_autogen_compat(test_session: AsyncSession):
    # 1. Test Adapter Message Exchange
    assistant = ConversableAgent(name="assistant", system_message="Assist user.")
    user = UserProxyAgent(name="user_proxy", human_input_mode="NEVER")

    user.initiate_chat(assistant, message="Hello, assistant!", max_turns=1)

    # Check history
    assert "assistant" in user.chat_history
    assert len(user.chat_history["assistant"]) >= 1
    assert user.chat_history["assistant"][0]["content"] == "Hello, assistant!"

    # 2. Test Converter
    tenant_id = "tenant-ag"
    agent_def = await convert_autogen_agent_to_agent_definition(
        db=test_session, tenant_id=tenant_id, agent=assistant
    )

    assert agent_def.name == "assistant"
    assert agent_def.instructions == "Assist user."

    # Convert chat history to session
    sess = await convert_autogen_chat_to_session(
        db=test_session,
        tenant_id=tenant_id,
        agent_id=agent_def.id,
        agent=user,
        recipient_name="assistant",
    )

    assert sess.tenant_id == tenant_id
    assert sess.session_metadata["recipient_name"] == "assistant"

    # 3. Test Importer
    source_code = """
assistant = ConversableAgent(name="AI", system_message="I am AI")
"""
    imported_agent = import_autogen_agent_from_source(source_code, target_variable="assistant")
    assert isinstance(imported_agent, ConversableAgent)
    assert imported_agent.name == "AI"


def test_compatibility_analyzer():
    # LangGraph Analysis
    source_lg = "StateGraph(dict)\n.compile()\nadd_conditional_edges\nSqliteSaver()"
    report = CompatibilityAnalyzer.analyze_source_code("langgraph", source_lg)
    assert report.score < 100.0
    assert report.status == "partially_compatible"
    assert len(report.remediation_steps) >= 2

    # CrewAI Analysis
    source_crew = "Agent()\nTask()\nCrew()\nProcess.hierarchical"
    report = CompatibilityAnalyzer.analyze_source_code("crewai", source_crew)
    assert report.score == 70.0
    assert report.status == "partially_compatible"
    assert "Hierarchical Process Flow" in [f["feature"] for f in report.analyzed_features]


@pytest.mark.asyncio
async def test_compat_api_endpoints(async_client: AsyncClient):
    # Test Analyze Endpoint
    source = "StateGraph(dict)\nbuilder.compile()"
    resp = await async_client.post(
        "/admin/compat/analyze", json={"framework": "langgraph", "source_code": source}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["framework"] == "langgraph"
    assert data["compatibility_score"] == 100.0
    assert data["status"] == "fully_compatible"

    # Test Migrate Endpoint (LangGraph)
    migrate_source = """
builder = StateGraph(state_schema=dict)
builder.add_node("step1", lambda x: x)
builder.set_entry_point("step1")
graph = builder.compile()
"""
    resp = await async_client.post(
        "/admin/compat/migrate",
        json={
            "framework": "langgraph",
            "source_code": migrate_source,
            "tenant_id": "tenant-api-test",
            "name": "API Workflow",
            "version": "1.0",
            "description": "Test via endpoint",
        },
    )
    if resp.status_code != 200:
        print("API Response Error:", resp.json())
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["status"] == "success"
    assert "workflow_definition_id" in res_data
    assert res_data["nodes_count"] == 1
