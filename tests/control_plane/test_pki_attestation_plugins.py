import hashlib

import pytest
from app.contracts.plugin import PluginManifest
from app.core.config import get_settings
from app.services.plugins.plugin_loader import PluginLoader
from app.services.security.attestation_service import NodeAttestationService
from app.services.security.pki_service import PKIService


@pytest.fixture
def mock_settings(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "pki_enabled", True)
    monkeypatch.setattr(settings, "attestation_mode", "enforcing")
    monkeypatch.setattr(settings, "plugin_signature_required", True)
    monkeypatch.setattr(settings, "rag_enabled", True)
    monkeypatch.setattr(settings, "tts_enabled", True)
    monkeypatch.setattr(settings, "lmstudio_enabled", True)
    monkeypatch.setattr(settings, "agent_runtime_enabled", False)
    return settings

class MockResult:
    def __init__(self, data):
        self.data = data
    def scalar(self):
        return self.data[0] if self.data else None
    def scalars(self):
        class MockScalars:
            def __init__(self, items):
                self.items = items
            def first(self):
                return self.items[0] if self.items else None
            def all(self):
                return self.items
        return MockScalars(self.data)

class MockAsyncSession:
    def __init__(self):
        self.added = []
    
    def add(self, obj):
        self.added.append(obj)
        
    async def commit(self):
        pass
        
    async def refresh(self, obj):
        pass
        
    async def execute(self, stmt):
        stmt_str = str(stmt).lower()
        if "certificate_inventory" in stmt_str or "certificateinventory" in stmt_str:
            # simple filter based on serial if it's in the statement
            items = [item for item in self.added if type(item).__name__ == "CertificateInventory"]
            if "serial_number" in stmt_str:
                for item in items:
                    if hasattr(item, "serial_number") and item.serial_number in stmt_str:
                        return MockResult([item])
            return MockResult(items)
        elif "plugin_registry" in stmt_str or "pluginregistry" in stmt_str:
            items = [item for item in self.added if type(item).__name__ == "PluginRegistry"]
            return MockResult(items)
        return MockResult([])

@pytest.fixture
def db_session():
    return MockAsyncSession()

class MockRedis:
    async def ping(self):
        return True

@pytest.mark.asyncio
async def test_pki_issue_verify(db_session, mock_settings):
    pki_service = PKIService(db_session)
    await pki_service.initialize_ca()
    
    cert_pem, key_pem = await pki_service.issue_certificate("test-client")
    assert cert_pem.startswith("-----BEGIN CERTIFICATE-----")
    
    is_valid = await pki_service.verify_certificate(cert_pem)
    assert is_valid is True

@pytest.mark.asyncio
async def test_pki_revoke(db_session, mock_settings):
    pki_service = PKIService(db_session)
    await pki_service.initialize_ca()
    
    cert_pem, _ = await pki_service.issue_certificate("revoke-test")
    
    # Parse cert to get serial number
    from cryptography import x509
    cert = x509.load_pem_x509_certificate(cert_pem.encode('utf-8'))
    serial = str(cert.serial_number)
    
    await pki_service.revoke_certificate(serial)
    
    is_valid = await pki_service.verify_certificate(cert_pem)
    assert is_valid is False

@pytest.mark.asyncio
async def test_attestation_report_enforcing(db_session, mock_settings):
    pki_service = PKIService(db_session)
    await pki_service.initialize_ca()
    
    att_service = NodeAttestationService(db_session)
    report = await att_service.generate_report()
    
    assert report.subject == "node-attestation"
    assert report.policy_result == "passed"
    assert "binary_hash" in report.measurements
    assert report.signature is not None
    
    is_valid = await att_service.verify_report(report)
    assert is_valid is True

@pytest.mark.asyncio
async def test_attestation_report_advisory(db_session, mock_settings, monkeypatch):
    monkeypatch.setattr(mock_settings, "attestation_mode", "advisory")
    pki_service = PKIService(db_session)
    await pki_service.initialize_ca()
    
    att_service = NodeAttestationService(db_session)
    report = await att_service.generate_report()
    
    # In advisory, even if hardware is fake or signature missing, verify_report returns True
    is_valid = await att_service.verify_report(report)
    assert is_valid is True

@pytest.mark.asyncio
async def test_plugin_invalid_checksum(db_session, mock_settings):
    pki_service = PKIService(db_session)
    await pki_service.initialize_ca()
    
    loader = PluginLoader(db_session)
    manifest = PluginManifest(
        name="bad-checksum-plugin",
        version="1.0",
        entrypoint="main.py",
        permissions=["read_data"],
        sha256="fakehash",
        signature="fakesig"
    )
    
    with pytest.raises(ValueError, match="Checksum mismatch"):
        await loader.load_plugin(manifest, b"actual binary content")

@pytest.mark.asyncio
async def test_plugin_missing_signature_enforcing(db_session, mock_settings):
    loader = PluginLoader(db_session)
    binary = b"actual binary content"
    actual_hash = hashlib.sha256(binary).hexdigest()
    
    manifest = PluginManifest(
        name="no-sig-plugin",
        version="1.0",
        entrypoint="main.py",
        permissions=["read_data"],
        sha256=actual_hash
    )
    
    with pytest.raises(ValueError, match="Signature required but not provided"):
        await loader.load_plugin(manifest, binary)

@pytest.mark.asyncio
async def test_plugin_missing_signature_advisory(db_session, mock_settings, monkeypatch):
    monkeypatch.setattr(mock_settings, "attestation_mode", "advisory")
    
    loader = PluginLoader(db_session)
    binary = b"actual binary content"
    actual_hash = hashlib.sha256(binary).hexdigest()
    
    manifest = PluginManifest(
        name="no-sig-plugin-advisory",
        version="1.0",
        entrypoint="main.py",
        permissions=["read_data"],
        sha256=actual_hash
    )
    
    # Should not raise exception, logs advisory warning instead
    plugin = await loader.load_plugin(manifest, binary)
    assert plugin.name == "no-sig-plugin-advisory"
    assert plugin.is_active is True

@pytest.mark.asyncio
async def test_readiness_enforcing(db_session, mock_settings):
    from app.api.system import ready
    
    redis_client = MockRedis()
    
    pki_service = PKIService(db_session)
    await pki_service.initialize_ca()
    
    # Mocking Alembic check
    class MockResult:
        def scalar(self): return "1"
        def scalars(self):
            class MockScalars:
                def first(self): return None
                def all(self): return []
            return MockScalars()

    class ReadinessMockSession(db_session.__class__):
        async def execute(self, stmt):
            if "alembic" in str(stmt).lower():
                return MockResult()
            if "select 1" in str(stmt).lower():
                return MockResult()
            return await super().execute(stmt)

    mock_db = ReadinessMockSession()
    mock_db.added = db_session.added

    response = await ready(mock_db, redis_client)
    assert isinstance(response, dict)
    assert response["status"] == "ready"
    assert response["dependencies"]["attestation"] == "ok"
