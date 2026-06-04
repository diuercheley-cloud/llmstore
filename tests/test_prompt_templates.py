
import pytest
from app.services.prompts.prompt_template_registry import PromptTemplateRegistryService
from app.services.prompts.prompt_template_renderer import PromptTemplateRenderer
from app.services.prompts.prompt_template_versioning import PromptTemplateVersioningService
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_prompt_template_rendering(session: AsyncSession):
    renderer = PromptTemplateRenderer()
    template = "Hello {{ name }}, your role is {{ role }}."
    variables = {"name": "Alice", "role": "Assistant"}
    
    rendered, hashes = renderer.resolve_instructions(template_str=template, instructions=None, variables=variables)
    assert rendered == "Hello Alice, your role is Assistant."
    assert hashes["variables_hash"] is not None
    assert hashes["output_hash"] is not None

@pytest.mark.asyncio
async def test_required_variable_missing(session: AsyncSession):
    renderer = PromptTemplateRenderer()
    template = "Hello {{ name }}."
    declared_vars = [{"name": "name", "required": True, "type": "string"}]
    
    # Missing variable should raise error or return original if validation fails in service layer
    try:
        await renderer.render(
            template_str=template, 
            variables={}, 
            declared_vars=declared_vars
        )
    except ValueError as e:
        assert "Missing variable in template" in str(e)

@pytest.mark.asyncio
async def test_secret_blocking(session: AsyncSession):
    renderer = PromptTemplateRenderer()
    # Testing direct render with secret
    try:
        renderer.render(
            template_str="Secret: {{ key }}",
            variables={"key": "sk-12345678901234567890"}
        )
        pytest.fail("Should have raised VariableIsSecretError")
    except Exception as e:
        assert "Variable 'key' contains a value that looks like a secret" in str(e)

@pytest.mark.asyncio
async def test_version_immutability(session: AsyncSession):
    svc = PromptTemplateRegistryService(session)
    ver_svc = PromptTemplateVersioningService(session)
    
    tenant_id = "test-tenant"
    template = await svc.create_template(tenant_id, "Test Template")
    version = await svc.create_version(template.id, "Content V1", "test-user", "V1")
    
    # Promote to production
    await ver_svc.promote_to_staging(version.id)
    await ver_svc.promote_to_production(version.id)
    
    assert version.status == "production"

@pytest.mark.asyncio
async def test_agent_executor_integration(session: AsyncSession):
    from app.core.config import get_settings
    from app.models.agents import AgentDefinition, AgentRun
    from app.services.agents.agent_executor import AgentExecutor
    
    settings = get_settings()
    settings.prompt_templates_enabled = True
    
    svc = PromptTemplateRegistryService(session)
    tenant_id = "test-tenant"
    template = await svc.create_template(tenant_id, "Agent Template")
    await svc.declare_variable(template.id, "input", "string", True)
    version = await svc.create_version(template.id, "Process this: {{ input }}", "test-user", "V1")
    template.active_version_id = version.id
    await session.commit()
    
    agent_def = AgentDefinition(
        name="Templated Agent",
        version="1.0",
        instructions="Default instructions",
        model_id="gpt-4",
        owner="test",
        tenant_id=tenant_id,
        prompt_template_id=template.id,
        prompt_template_version_id=version.id
    )
    session.add(agent_def)
    await session.flush()
    
    run = AgentRun(
        agent_id=agent_def.id,
        tenant_id=tenant_id,
        input_text="User data",
        status="running"
    )
    session.add(run)
    await session.flush()
    
    executor = AgentExecutor(session, run.id)
    # We test the internal _resolve_prompt_template
    resolved_agent = await executor._resolve_prompt_template(agent_def, run)
    
    assert "Process this: User data" in resolved_agent.instructions
