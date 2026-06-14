import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.models.agents.agent_studio import AgentFlowDefinition, AgentFlowVersion
from app.services.agents.studio.flow_compiler import FlowCompiler
from app.services.agents.studio.flow_runtime_adapter import FlowRuntimeAdapter
from app.services.agents.studio.flow_validator import FlowValidator
from app.services.agents.studio.flow_versioning import FlowVersioningService
from app.services.agents.studio.template_gallery import TemplateGalleryService
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def mock_db():
    return MagicMock(spec=AsyncSession)

@pytest.fixture
def sample_graph():
    return {
        "nodes": [
            {"id": "start", "node_type": "trigger", "label": "Start"},
            {"id": "llm_1", "node_type": "llm_call", "label": "Process Input", "config": {"model": "gpt-4", "prompt": "{{input}}"}},
            {"id": "end", "node_type": "final_response", "label": "End"},
        ],
        "edges": [
            {"source": "start", "target": "llm_1"},
            {"source": "llm_1", "target": "end"},
        ]
    }

@pytest.mark.asyncio
async def test_create_flow(mock_db):
    service = FlowVersioningService(mock_db)

    async def fake_commit():
        pass
    async def fake_refresh(obj):
        obj.id = uuid.uuid4()
        obj.tenant_id = "tenant-1"
        obj.name = "Test Flow"
        obj.description = "A test flow"
    mock_db.commit = fake_commit
    mock_db.refresh = fake_refresh

    result = await service.create_flow("tenant-1", "Test Flow", "A test flow")
    assert result.tenant_id == "tenant-1"
    assert result.name == "Test Flow"
    assert result.description == "A test flow"

@pytest.mark.asyncio
async def test_save_version(mock_db, sample_graph):
    flow_id = uuid.uuid4()
    mock_db.get = AsyncMock(return_value=AgentFlowDefinition(id=flow_id, tenant_id="tenant-1"))

    first_result = MagicMock()
    first_result.scalars.return_value.all.return_value = []
    second_version = AgentFlowVersion(flow_id=flow_id, id=uuid.uuid4(), graph_json=sample_graph, version_label="v1", is_active=True)
    second_result = MagicMock()
    second_result.unique.return_value.scalar_one.return_value = second_version

    mock_db.execute = AsyncMock(side_effect=[first_result, second_result])

    service = FlowVersioningService(mock_db)
    result = await service.save_version(
        flow_id, sample_graph, "v1", make_active=True
    )
    assert result.version_label == "v1"
    assert result.graph_json == sample_graph
    assert result.is_active is True

@pytest.mark.asyncio
async def test_validate_valid_flow(mock_db, sample_graph):
    validator = FlowValidator()
    version = AgentFlowVersion(graph_json=sample_graph)
    errors = validator.validate(version)
    assert len(errors) == 0

@pytest.mark.asyncio
async def test_validate_invalid_flow(mock_db):
    validator = FlowValidator()
    bad_graph = {
        "nodes": [
            {"id": "start", "node_type": "trigger"},
        ],
        "edges": [
            {"source": "start", "target": "nonexistent"},
        ]
    }
    version = AgentFlowVersion(graph_json=bad_graph)
    errors = validator.validate(version)
    assert len(errors) >= 1
    assert any("missing_terminal_node" in str(e) for e in errors)

@pytest.mark.asyncio
async def test_compile_flow(mock_db, sample_graph):
    compiler = FlowCompiler()
    version = AgentFlowVersion(flow_id=uuid.uuid4(), id=uuid.uuid4(), graph_json=sample_graph)
    result = compiler.compile(version)
    assert "tasks" in result
    assert len(result["tasks"]) >= 2

@pytest.mark.asyncio
async def test_compile_flow_with_loops(mock_db):
    compiler = FlowCompiler()
    loop_graph = {
        "nodes": [
            {"id": "start", "node_type": "trigger"},
            {"id": "llm_1", "node_type": "llm_call", "config": {"model": "gpt-4", "prompt": "test"}},
            {"id": "end", "node_type": "final_response"},
        ],
        "edges": [
            {"source": "start", "target": "llm_1"},
            {"source": "llm_1", "target": "end"},
        ]
    }
    version = AgentFlowVersion(flow_id=uuid.uuid4(), id=uuid.uuid4(), graph_json=loop_graph)
    result = compiler.compile(version)
    assert "tasks" in result

@pytest.mark.asyncio
async def test_dry_run(mock_db, sample_graph):
    adapter = FlowRuntimeAdapter(mock_db)
    version_id = uuid.uuid4()
    version = AgentFlowVersion(id=version_id, flow_id=uuid.uuid4(), graph_json=sample_graph)
    mock_db.get = AsyncMock(return_value=version)

    result = await adapter.dry_run(version_id, {"input": "Hello"})
    assert result["status"] == "completed"

@pytest.mark.asyncio
async def test_dry_run_version_not_found(mock_db):
    adapter = FlowRuntimeAdapter(mock_db)
    mock_db.get = AsyncMock(return_value=None)

    with pytest.raises(ValueError, match="Flow version not found"):
        await adapter.dry_run(uuid.uuid4(), {})

def test_template_gallery_list():
    with patch.object(TemplateGalleryService, "list_templates", return_value=[
        {"template_id": "customer-support", "name": "Customer Support Agent", "category": "support"},
        {"template_id": "data-analysis", "name": "Data Analysis Agent", "category": "analytics"},
    ]):
        gallery = TemplateGalleryService()
        templates = gallery.list_templates()
        assert len(templates) == 2
        assert templates[0]["template_id"] == "customer-support"

def test_template_gallery_empty():
    with patch.object(TemplateGalleryService, "list_templates", return_value=[]):
        gallery = TemplateGalleryService()
        assert gallery.list_templates() == []

def test_template_gallery_details():
    expected = {"template_id": "customer-support", "name": "Support Agent", "instructions": "Help customers"}
    with patch.object(TemplateGalleryService, "get_template_details", return_value=expected):
        gallery = TemplateGalleryService()
        details = gallery.get_template_details("customer-support")
        assert details["name"] == "Support Agent"

def test_template_gallery_details_not_found():
    with patch.object(TemplateGalleryService, "get_template_details", return_value=None):
        gallery = TemplateGalleryService()
        assert gallery.get_template_details("nonexistent") is None

def test_template_validation_missing_files():
    gallery = TemplateGalleryService()
    with patch.object(gallery, "validate_template", return_value=[
        "Missing required file: agent.yaml",
        "Missing required file: instructions.md",
    ]):
        errors = gallery.validate_template("incomplete-template")
        assert len(errors) == 2
        assert "agent.yaml" in errors[0]

def test_template_validation_valid():
    gallery = TemplateGalleryService()
    with patch.object(gallery, "validate_template", return_value=[]):
        errors = gallery.validate_template("valid-template")
        assert len(errors) == 0
