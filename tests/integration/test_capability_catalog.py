import uuid

import pytest
from app.models.agents.agent_catalog import AgentCapabilityCatalogEntry
from app.services.agents.catalog.capability_catalog import CapabilityCatalogService
from app.services.agents.catalog.signature_verifier import SignatureVerifier
from app.services.agents.catalog.supply_chain_verifier import SupplyChainVerifier
from app.services.plugins.plugin_manifest import PluginManifest


@pytest.mark.asyncio
async def test_capability_install_and_approve(session):
    service = CapabilityCatalogService(session)
    entry_data = {
        "name": "test-plugin",
        "category": "plugin",
        "version": "1.0.0",
        "owner": "test-owner",
        "manifest": {"name": "test"},
        "permissions": ["net:google.com"],
        "status": "draft",
    }
    entry = await service.install_entry(entry_data)
    assert entry.name == "test-plugin"
    assert entry.status == "draft"

    approver_id = uuid.uuid4()
    approved = await service.approve_entry(entry.id, approver_id, "Approved for beta")
    assert approved.status == "approved"


def test_supply_chain_verifier():
    content = b"plugin code"
    import hashlib

    expected_checksum = hashlib.sha256(content).hexdigest()
    assert SupplyChainVerifier.verify_checksum(content, expected_checksum) is True
    assert SupplyChainVerifier.verify_checksum(content, "wrong") is False


def test_signature_verifier():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    private_key = ec.generate_private_key(ec.SECP256R1())
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()

    data = "test data"
    signature_hex = SignatureVerifier.sign_data(data, private_pem)
    assert signature_hex is not None
    assert SignatureVerifier.verify_signature(data, signature_hex, public_pem) is True
    assert SignatureVerifier.verify_signature(data, "00" * 64, public_pem) is False


def test_plugin_manifest_validation():
    manifest_data = {
        "name": "my-plugin",
        "version": "1.0.0",
        "owner": "acme",
        "permissions": ["fs:read"],
        "capabilities": ["text-processing"],
        "entrypoint": "main.py",
        "checksum_sha256": "abc",
    }
    manifest = PluginManifest(**manifest_data)
    assert manifest.name == "my-plugin"
    assert manifest.risk_level == "medium"


@pytest.mark.asyncio
async def test_disable_capability(session):
    service = CapabilityCatalogService(session)
    entry = AgentCapabilityCatalogEntry(
        name="to-disable",
        category="connector",
        version="1.0.0",
        owner="test",
        manifest={},
        permissions=[],
    )
    session.add(entry)
    await session.commit()

    await service.disable_entry(entry.id)
    await session.refresh(entry)
    assert entry.status == "disabled"
