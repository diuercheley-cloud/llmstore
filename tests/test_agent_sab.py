import uuid

import pytest
from app.models.agents import AgentDefinition
from app.services.agents.sab.sab_exporter import SABExporter
from app.services.agents.sab.sab_importer import SABImporter


@pytest.fixture
async def setup_agent(session):
    agent = AgentDefinition(
        id=uuid.uuid4(),
        name="Portable Agent",
        version="1.0.0",
        model_id="test",
        owner="test",
        tenant_id="t1",
        instructions="do magic"
    )
    session.add(agent)
    await session.commit()
    return agent

@pytest.mark.asyncio
async def test_export_gera_manifest(session, setup_agent):
    exporter = SABExporter(session)
    manifest = await exporter.export_agent(setup_agent.id)
    
    assert manifest.name == "Portable Agent"
    assert "manifest" in manifest.checksums
    assert manifest.signature is not None

@pytest.mark.asyncio
async def test_import_cria_draft(session, setup_agent):
    exporter = SABExporter(session)
    manifest = await exporter.export_agent(setup_agent.id)
    
    importer = SABImporter(session)
    imported_agent = await importer.import_agent(manifest, "tenant_new")
    
    assert imported_agent.tenant_id == "tenant_new"
    assert imported_agent.status == "draft"
    assert "[Imported]" in imported_agent.name

@pytest.mark.asyncio
async def test_checksum_invalido_bloqueia(session, setup_agent):
    exporter = SABExporter(session)
    manifest = await exporter.export_agent(setup_agent.id)
    
    # Tamper manifest
    manifest.instructions = "malicious instructions"
    
    importer = SABImporter(session)
    with pytest.raises(ValueError, match="Checksum mismatch"):
        await importer.import_agent(manifest, "t2")

@pytest.mark.asyncio
async def test_memory_snapshot_com_secret_bloqueia(session, setup_agent):
    exporter = SABExporter(session)
    manifest = await exporter.export_agent(setup_agent.id)
    
    # Add memory with secret
    manifest.memory_snapshot = [{"id": "m1", "content": "My key is sk-12345"}]
    # Update checksum and signature to pass integrity check but fail security check
    import hashlib
    import json
    data_to_hash = manifest.model_dump(exclude={"checksums", "signature"})
    payload = json.dumps(data_to_hash, sort_keys=True).encode()
    new_checksum = hashlib.sha256(payload).hexdigest()
    manifest.checksums["manifest"] = new_checksum
    manifest.signature = f"sig:{new_checksum}:prod_key"
    
    importer = SABImporter(session)
    with pytest.raises(ValueError, match="Security violation: memory snapshot contains raw secrets"):
        await importer.import_agent(manifest, "t2")

@pytest.mark.asyncio
async def test_assinatura_invalida_bloqueia(session, setup_agent):
    exporter = SABExporter(session)
    manifest = await exporter.export_agent(setup_agent.id)
    
    manifest.signature = "sig:invalid:fake"
    
    importer = SABImporter(session)
    with pytest.raises(ValueError, match="Invalid signature"):
        await importer.import_agent(manifest, "t2")
