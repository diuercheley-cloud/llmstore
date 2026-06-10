import hashlib
import uuid

import pytest
from app.core.config import get_settings
from app.models.agents.agents import AgentBundleSignature, AgentBundleVersion
from app.services.agents.agent_bundle_verifier import AgentBundleVerifierService


@pytest.mark.asyncio
async def test_pacote_externo_unsigned_bloqueia(session):
    service = AgentBundleVerifierService(session)
    v_id = uuid.uuid4()
    content = b"test"
    version = AgentBundleVersion(id=v_id, version="1.0", checksum_sha256=hashlib.sha256(content).hexdigest(), entry_id=uuid.uuid4(), manifest_json="{}")
    session.add(version)
    await session.commit()
    
    res = await service.verify_bundle(v_id, content, is_internal=False)
    assert res["passed"] is False
    assert "Signature required for external" in res["reason"]

@pytest.mark.asyncio
async def test_pacote_interno_unsigned_bloqueia_em_production(session, monkeypatch):
    service = AgentBundleVerifierService(session)
    settings = get_settings()
    monkeypatch.setattr(settings, "app_env", "production")
    
    # We must patch the verifier's settings reference or its attributes
    monkeypatch.setattr(service.settings, "app_env", "production", raising=False)
    monkeypatch.setattr(service.settings, "agent_internal_bundle_signature_required_in_production", True, raising=False)
    
    v_id = uuid.uuid4()
    content = b"test2"
    version = AgentBundleVersion(id=v_id, version="1.0", checksum_sha256=hashlib.sha256(content).hexdigest(), entry_id=uuid.uuid4(), manifest_json="{}")
    session.add(version)
    await session.commit()
    
    res = await service.verify_bundle(v_id, content, is_internal=True)
    assert res["passed"] is False
    assert "Signature required for internal packages in production" in res["reason"]

@pytest.mark.asyncio
async def test_pacote_interno_unsigned_permitido_em_dev_com_warning(session, caplog, monkeypatch):
    service = AgentBundleVerifierService(session)
    settings = get_settings()
    monkeypatch.setattr(service.settings, "app_env", "development", raising=False)
    monkeypatch.setattr(service.settings, "allow_unsigned_internal_bundles", True, raising=False)
    v_id = uuid.uuid4()
    content = b"test3"
    version = AgentBundleVersion(id=v_id, version="1.0", checksum_sha256=hashlib.sha256(content).hexdigest(), entry_id=uuid.uuid4(), manifest_json="{}")
    session.add(version)
    await session.commit()
    
    res = await service.verify_bundle(v_id, content, is_internal=True)
    assert res["passed"] is True
    assert "[AUDIT WARNING] Permitting unsigned internal bundle" in caplog.text

@pytest.mark.asyncio
async def test_checksum_invalido_bloqueia(session):
    service = AgentBundleVerifierService(session)
    v_id = uuid.uuid4()
    content = b"test4"
    version = AgentBundleVersion(id=v_id, version="1.0", checksum_sha256="wrong_checksum", entry_id=uuid.uuid4(), manifest_json="{}")
    session.add(version)
    await session.commit()
    
    res = await service.verify_bundle(v_id, content, is_internal=False)
    assert res["passed"] is False
    assert "Checksum mismatch" in res["reason"]

@pytest.mark.asyncio
async def test_assinatura_invalida_bloqueia(session):
    service = AgentBundleVerifierService(session)
    v_id = uuid.uuid4()
    content = b"test5"
    checksum = hashlib.sha256(content).hexdigest()
    version = AgentBundleVersion(id=v_id, version="1.0", checksum_sha256=checksum, entry_id=uuid.uuid4(), manifest_json="{}")
    sig = AgentBundleSignature(version_id=v_id, signature_type="ed25519", signature_value="invalid_sig", public_key_id="k1", signed_by="test")
    session.add_all([version, sig])
    await session.commit()
    
    res = await service.verify_bundle(v_id, content, is_internal=False)
    assert res["passed"] is False
    assert "Invalid signature" in res["reason"]

@pytest.mark.asyncio
async def test_trust_report_gerado(session):
    service = AgentBundleVerifierService(session)
    v_id = uuid.uuid4()
    content = b"test6"
    checksum = hashlib.sha256(content).hexdigest()
    version = AgentBundleVersion(id=v_id, version="1.0", checksum_sha256=checksum, entry_id=uuid.uuid4(), manifest_json="{}")
    sig = AgentBundleSignature(version_id=v_id, signature_type="ed25519", signature_value=f"sig:{checksum}:k1", public_key_id="k1", signed_by="test")
    session.add_all([version, sig])
    await session.commit()
    
    report = await service.generate_trust_report(v_id)
    assert report.is_signed is True
    assert report.trust_score == 1.0

@pytest.mark.asyncio
async def test_capability_sem_manifest_falha(session):
    service = AgentBundleVerifierService(session)
    v_id = uuid.uuid4()
    content = b"test7"
    # missing checksum_sha256
    version = AgentBundleVersion(id=v_id, version="1.0", checksum_sha256="", entry_id=uuid.uuid4(), manifest_json="{}")
    session.add(version)
    await session.commit()
    
    res = await service.verify_bundle(v_id, content, is_internal=False)
    assert res["passed"] is False
    assert "Manifest checksum is missing" in res["reason"]
