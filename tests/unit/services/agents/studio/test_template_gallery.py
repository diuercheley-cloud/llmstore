# Owner: agent-platform

import pytest
from app.services.agents.studio.template_gallery import TemplateGalleryService


@pytest.fixture
def temp_templates(tmp_path):
    # Setup dummy templates
    t1 = tmp_path / "t1"
    t1.mkdir()
    (t1 / "agent.yaml").write_text("name: t1\nmodel: gpt-4o")
    (t1 / "instructions.md").write_text("instr")
    (t1 / "eval_suite.json").write_text("{}")
    
    t2 = tmp_path / "t2"
    t2.mkdir()
    (t2 / "agent.yaml").write_text("name: t2\nmodel: gpt-4o")
    
    return tmp_path

def test_list_templates(temp_templates):
    service = TemplateGalleryService(templates_root=str(temp_templates))
    templates = service.list_templates()
    
    assert len(templates) >= 2
    assert any(t["template_id"] == "t1" for t in templates)

def test_get_template_details(temp_templates):
    service = TemplateGalleryService(templates_root=str(temp_templates))
    details = service.get_template_details("t1")
    
    assert details["name"] == "t1"
    assert details["instructions"] == "instr"

def test_validate_template(temp_templates):
    service = TemplateGalleryService(templates_root=str(temp_templates))
    
    # Valid
    errors = service.validate_template("t1")
    assert len(errors) == 0
    
    # Invalid (missing files)
    errors = service.validate_template("t2")
    assert len(errors) > 0
    assert any("Missing required file" in e for e in errors)
