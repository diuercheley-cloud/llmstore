import pytest
import uuid
import json
from app.services.agents.agent_marketplace import AgentMarketplaceService
from app.core.config import get_settings

@pytest.mark.asyncio
async def test_bundle_install_valid(session):
    settings = get_settings()
    settings.agent_bundle_install_enabled = True
    settings.agent_bundle_signature_required = False
    
    service = AgentMarketplaceService(session)
    
    bundle_data = {
        "name": "test-agent",
        "version": "1.0.0",
        "category": "test",
        "agent_definition": {
            "instructions": "test instructions",
            "allowed_tools": ["t1"]
        }
    }
    
    content = json.dumps(bundle_data).encode("utf-8")
    install = await service.install_bundle("t1", content, "bundle.json")
    
    assert install.status == "installed"
    assert install.is_enabled is False
    
    # Check if agent definition was created
    from app.services.agents import agent_state
    agent = await agent_state.get_agent_definition(session, install.agent_id)
    assert agent.name == "test-agent"
    assert agent.instructions == "test instructions"

@pytest.mark.asyncio
async def test_bundle_signature_required_failure(session):
    settings = get_settings()
    settings.agent_bundle_install_enabled = True
    settings.agent_bundle_signature_required = True
    
    service = AgentMarketplaceService(session)
    bundle_data = {"name": "unsigned", "version": "1"}
    content = json.dumps(bundle_data).encode("utf-8")
    
    with pytest.raises(ValueError, match="signature is required"):
        await service.install_bundle("t1", content, "bundle.json")

@pytest.mark.asyncio
async def test_trust_report_generation(session):
    settings = get_settings()
    settings.agent_bundle_install_enabled = True
    
    service = AgentMarketplaceService(session)
    bundle_data = {"name": "trusted", "version": "1", "agent_definition": {}}
    content = json.dumps(bundle_data).encode("utf-8")
    
    install = await service.install_bundle("t1", content, "bundle.json")
    report = await service.get_trust_report(install.version_id)
    
    assert report is not None
    assert report.trust_score >= 0.0
    assert report.is_signed is False
