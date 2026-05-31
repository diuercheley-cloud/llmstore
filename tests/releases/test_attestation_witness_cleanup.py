import pytest
import uuid
import sys
import os
import hashlib
from unittest.mock import MagicMock, AsyncMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "control_plane"))

from app.services.agents.code_interpreter.sandbox_attestation import AttestationService, SandboxAttestation
from app.services.operations.plugin_supply_chain.sbom_placeholder import PluginSBOMPlaceholderService
from app.services.inference import witness_federation
from app.models.commercial_witness import CommercialWitness, CommercialWitnessSignature, CommercialWitnessAuditEvent
from app.models.commercial_merkle_timelines import CommercialMerkleTimeline
from app.models.operations.plugin_supply_chain import PluginSBOMPlaceholder
from app.services.inference import confidential_runtime
from app.utils.crypto_signer import sign_payload
from app.models.commercial_confidential_runtime import (
    CommercialConfidentialInferenceSession,
    CommercialConfidentialRuntimeProfile,
    CommercialConfidentialRuntimeAuditEvent
)

@pytest.mark.asyncio
async def test_sbom_placeholder_fails_in_production():
    svc = PluginSBOMPlaceholderService()
    provenance = MagicMock()
    provenance.client_id = uuid.uuid4()
    provenance.id = "provenance-123"
    
    # Non-production allows generation
    with patch("app.core.config.get_settings") as mock_settings:
        mock_settings.return_value.app_env = "development"
        placeholder = svc.generate_sbom_placeholder(provenance, {}, [])
        assert isinstance(placeholder, PluginSBOMPlaceholder)
        
        val_res = svc.validate_sbom_placeholder(placeholder)
        assert val_res["valid"] is True

    # Production blocks generation and validation
    with patch("app.core.config.get_settings") as mock_settings:
        mock_settings.return_value.app_env = "production"
        with pytest.raises(RuntimeError, match="Placeholder SBOM is blocked in production mode"):
            svc.generate_sbom_placeholder(provenance, {}, [])
            
        dummy_placeholder = PluginSBOMPlaceholder(
            id="dummy",
            client_id=uuid.uuid4(),
            provenance_record_id="provenance-123",
            sbom_format="placeholder_v1",
            dependency_summary_json={},
            denied_dependencies_json=[],
            sbom_hash="hash",
            immutable_hash="hash"
        )
        with pytest.raises(RuntimeError, match="Placeholder SBOM is blocked in production mode"):
            svc.validate_sbom_placeholder(dummy_placeholder)

@pytest.mark.asyncio
async def test_attestation_requires_signature_in_production():
    profile = MagicMock()
    profile.provider = "gvisor"
    profile.kernel_isolation_level = "gvisor"
    profile.runtime_version = "1.0.0"
    profile.network_mode = "none"
    profile.filesystem_mode = "read-only"
    profile.limits = {}
    
    key_path = "config/receipts_private_key_test.pem"
    if os.path.exists(key_path):
        try:
            os.remove(key_path)
        except Exception:
            pass
            
    # Verify in production fails if signature is missing or placeholder
    with patch("app.core.config.get_settings") as mock_settings, \
         patch.dict(os.environ, {
             "CRYPTO_RECEIPTS_PRIVATE_KEY_PATH": key_path,
             "CRYPTO_RECEIPTS_REQUIRE_SIGNATURE": "false"
         }):
        mock_settings.return_value.app_env = "production"
        
        # Missing signature
        att = {
            "provider": "gvisor",
            "isolation_level": "gvisor",
            "runtime_version": "1.0.0",
            "network_policy": "none",
            "filesystem_policy": "read-only",
            "resource_limits": {},
            "artifact_hashes": [],
            "attestation_time": "2026-05-29T12:00:00",
            "signature": None
        }
        assert AttestationService.verify_attestation(att) is False
        
        # Signature
        att["signature"] = "placeholder-signature-fallback"
        assert AttestationService.verify_attestation(att) is False
        
        # Real signature should pass
        # Let's generate a valid signature first using the real functions
        from app.services.inference.cryptographic_receipts import sign_payload
        import json
        payload_data = {k: v for k, v in att.items() if k != "signature"}
        canonical_str = json.dumps(payload_data, sort_keys=True)
        att["signature"] = sign_payload(canonical_str)
        
        assert AttestationService.verify_attestation(att) is True

@pytest.mark.asyncio
async def test_witness_signatures_fail_if_placeholders_in_production():
    db = AsyncMock()
    
    timeline = CommercialMerkleTimeline(id=uuid.uuid4(), merkle_root="root123", status="sealed")
    witness = CommercialWitness(id=uuid.uuid4(), status="active")
    
    sig = CommercialWitnessSignature(
        id=uuid.uuid4(),
        timeline_id=timeline.id,
        witness_id=witness.id,
        merkle_root="root123",
        signature="placeholder-signature-fake",
        verification_status="valid"
    )
    
    db.execute.side_effect = [
        MagicMock(scalar_one_or_none=lambda: sig),
        MagicMock(scalar_one_or_none=lambda: witness),
        MagicMock(scalar_one_or_none=lambda: timeline)
    ]
    
    key_path = "config/receipts_private_key_test.pem"
    if os.path.exists(key_path):
        try:
            os.remove(key_path)
        except Exception:
            pass
            
    with patch("app.services.inference.witness_federation.get_settings") as mock_settings, \
         patch.dict(os.environ, {
             "CRYPTO_RECEIPTS_PRIVATE_KEY_PATH": key_path,
             "CRYPTO_RECEIPTS_REQUIRE_SIGNATURE": "false"
         }):
        mock_settings.return_value.app_env = "production"
        mock_settings.return_value.admin_token = "admin"
        
        # In production, fake placeholder verification fails
        is_valid = await witness_federation.verify_witness_signature(db, sig.id)
        assert is_valid is False
        assert sig.verification_status == "invalid"

@pytest.mark.asyncio
async def test_witness_unsigned_event_fails():
    db = AsyncMock()
    from datetime import datetime
    
    # Event with fake/invalid hash
    event = CommercialWitnessAuditEvent(
        id=uuid.uuid4(),
        event_type="signature_received",
        witness_id=uuid.uuid4(),
        timeline_id=uuid.uuid4(),
        summary="Some summary",
        immutable_hash="invalid-hash-value-123",
        created_at=datetime.utcnow()
    )
    
    db.execute.side_effect = [
        MagicMock(scalar_one_or_none=lambda: event)
    ]
    
    key_path = "config/receipts_private_key_test.pem"
    if os.path.exists(key_path):
        try:
            os.remove(key_path)
        except Exception:
            pass
            
    with patch("app.services.inference.witness_federation.get_settings") as mock_settings, \
         patch.dict(os.environ, {
             "CRYPTO_RECEIPTS_PRIVATE_KEY_PATH": key_path,
             "CRYPTO_RECEIPTS_REQUIRE_SIGNATURE": "false"
         }):
        mock_settings.return_value.app_env = "production"
        is_valid = await witness_federation.verify_witness_audit_event(db, event.id)
        assert is_valid is False

@pytest.mark.asyncio
async def test_confidential_cleanup_generates_receipt():
    db = AsyncMock()
    
    profile = CommercialConfidentialRuntimeProfile(
        id=uuid.uuid4(),
        profile_name="test-profile",
        max_retention_seconds=0
    )
    session = CommercialConfidentialInferenceSession(
        id=uuid.uuid4(),
        client_id="client-abc",
        retention_policy_applied=False
    )
    
    key_path = "config/receipts_private_key_test.pem"
    if os.path.exists(key_path):
        try:
            os.remove(key_path)
        except Exception:
            pass
            
    with patch("app.services.inference.confidential_runtime.get_settings") as mock_settings, \
         patch("app.services.inference.confidential_runtime.log_confidential_audit") as mock_log, \
         patch.dict(os.environ, {
             "CRYPTO_RECEIPTS_PRIVATE_KEY_PATH": key_path,
             "CRYPTO_RECEIPTS_REQUIRE_SIGNATURE": "false"
         }):
        mock_settings.return_value.app_env = "production"
        mock_settings.return_value.commercial_confidential_default_retention_seconds = 0
        
        await confidential_runtime.apply_retention_policy(db, session, profile)
        
        assert session.retention_policy_applied is True
        # Verify clean_up log audit was called
        mock_log.assert_called_once()
        args, kwargs = mock_log.call_args
        # Event type should be retention_policy_applied
        assert args[2] == "retention_policy_applied"
        # Summary should contain the cleanup receipt
        assert "Receipt:" in args[3]
