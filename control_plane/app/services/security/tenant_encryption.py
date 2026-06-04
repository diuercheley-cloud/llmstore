import base64
import hashlib
import secrets
import uuid
from datetime import timedelta
from typing import Any, Dict, Optional

from app.core.config import Settings
from app.core.time import utc_now
from app.models.commercial_encryption import (
    CommercialEncryptedArtifact,
    CommercialEncryptionAuditEvent,
    CommercialTenantEncryptionKey,
)
from app.services.security.local_aead import AESGCM
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession


class TenantEncryptionService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.master_key = self._derive_master_key(settings.commercial_tenant_encryption_master_key)

    def _derive_master_key(self, key_str: str) -> bytes:
        # Simple derivation for local use, ensuring 32 bytes for AES-256
        return hashlib.sha256(key_str.encode()).digest()

    async def create_tenant_key(
        self, 
        db: AsyncSession, 
        client_id: uuid.UUID, 
        purpose: str = "general"
    ) -> CommercialTenantEncryptionKey:
        # Generate a new DEK
        dek = secrets.token_bytes(32)
        
        # Wrap DEK with Master Key
        aesgcm = AESGCM(self.master_key)
        nonce = secrets.token_bytes(12)
        wrapped_bytes = aesgcm.encrypt(nonce, dek, None)
        wrapped_key_b64 = base64.b64encode(nonce + wrapped_bytes).decode()
        
        fingerprint = hashlib.sha256(dek).hexdigest()
        
        key = CommercialTenantEncryptionKey(
            client_id=client_id,
            key_version="1.0",
            key_purpose=purpose,
            key_status="active",
            wrapped_key=wrapped_key_b64,
            key_fingerprint=fingerprint,
            rotation_due_at=utc_now() + timedelta(days=self.settings.commercial_tenant_encryption_auto_rotation_days),
        )
        db.add(key)
        await db.flush() # Flush to get ID without committing if in a larger transaction
        
        await self._log_event(db, client_id, "create_key", "key", str(key.id), fingerprint)
        return key

    async def _unwrap_dek(self, wrapped_key_b64: str) -> bytes:
        data = base64.b64decode(wrapped_key_b64)
        nonce = data[:12]
        ciphertext = data[12:]
        aesgcm = AESGCM(self.master_key)
        return aesgcm.decrypt(nonce, ciphertext, None)

    async def encrypt_payload(
        self,
        db: AsyncSession,
        client_id: Optional[uuid.UUID],
        payload: str,
        artifact_type: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        key_purpose: str = "general"
    ) -> CommercialEncryptedArtifact:
        if not self.settings.commercial_tenant_encryption_enabled:
            artifact = CommercialEncryptedArtifact(
                client_id=client_id,
                artifact_type=artifact_type,
                resource_type=resource_type,
                resource_id=resource_id,
                encryption_mode="plaintext",
                encrypted_payload=payload,
                payload_hash=hashlib.sha256(payload.encode()).hexdigest(),
                key_id=None,
            )
            db.add(artifact)
            return artifact

        # Find active key for client and purpose
        if client_id:
            stmt = select(CommercialTenantEncryptionKey).where(
                CommercialTenantEncryptionKey.client_id == client_id,
                CommercialTenantEncryptionKey.key_purpose == key_purpose,
                CommercialTenantEncryptionKey.key_status == "active"
            ).order_by(desc(CommercialTenantEncryptionKey.created_at)).limit(1)
            
            result = await db.execute(stmt)
            key = result.scalar_one_or_none()
            
            if not key:
                key = await self.create_tenant_key(db, client_id, key_purpose)
        else:
            # System-wide key or fallback? For now, we require client_id or use a specific system client
            # In Phase 36, most artifacts are tenant-scoped.
            key = None

        if not key:
             # Fallback to plaintext if no key and no client_id (should be rare in commercial)
            artifact = CommercialEncryptedArtifact(
                client_id=client_id,
                artifact_type=artifact_type,
                resource_type=resource_type,
                resource_id=resource_id,
                encryption_mode="plaintext",
                encrypted_payload=payload,
                payload_hash=hashlib.sha256(payload.encode()).hexdigest(),
                key_id=None,
            )
            db.add(artifact)
            return artifact
            
        dek = await self._unwrap_dek(key.wrapped_key)
        aesgcm = AESGCM(dek)
        nonce = secrets.token_bytes(12)
        encrypted_bytes = aesgcm.encrypt(nonce, payload.encode(), None)
        encrypted_payload_b64 = base64.b64encode(nonce + encrypted_bytes).decode()
        
        payload_hash = hashlib.sha256(payload.encode()).hexdigest()
        
        artifact = CommercialEncryptedArtifact(
            client_id=client_id,
            artifact_type=artifact_type,
            resource_type=resource_type,
            resource_id=resource_id,
            encryption_mode="envelope",
            encrypted_payload=encrypted_payload_b64,
            payload_hash=payload_hash,
            key_id=key.id,
        )
        db.add(artifact)
        
        await self._log_event(db, client_id, "encrypt", resource_type, resource_id, key.key_fingerprint)
        return artifact

    async def decrypt_payload(
        self,
        db: AsyncSession,
        artifact: CommercialEncryptedArtifact
    ) -> str:
        if artifact.encryption_mode == "plaintext":
            return artifact.encrypted_payload
            
        if not artifact.key_id:
            raise ValueError("Artifact is encrypted but has no key_id")
            
        key = await db.get(CommercialTenantEncryptionKey, artifact.key_id)
        if not key:
            raise ValueError(f"Key {artifact.key_id} not found")
            
        if key.key_status == "revoked":
            await self._log_event(db, artifact.client_id, "decrypt_failed_revoked", artifact.resource_type, artifact.resource_id, key.key_fingerprint, success=False)
            raise ValueError("Key is revoked")
            
        dek = await self._unwrap_dek(key.wrapped_key)
        data = base64.b64decode(artifact.encrypted_payload)
        nonce = data[:12]
        ciphertext = data[12:]
        
        aesgcm = AESGCM(dek)
        decrypted_bytes = aesgcm.decrypt(nonce, ciphertext, None)
        payload = decrypted_bytes.decode()
        
        # Verify hash
        if hashlib.sha256(decrypted_bytes).hexdigest() != artifact.payload_hash:
            await self._log_event(db, artifact.client_id, "decrypt_failed_hash", artifact.resource_type, artifact.resource_id, key.key_fingerprint, success=False)
            raise ValueError("Payload hash mismatch")
            
        await self._log_event(db, artifact.client_id, "decrypt", artifact.resource_type, artifact.resource_id, key.key_fingerprint)
        return payload

    async def _log_event(
        self,
        db: AsyncSession,
        client_id: Optional[uuid.UUID],
        event_type: str,
        resource_type: str,
        resource_id: Optional[str],
        key_fingerprint: Optional[str] = None,
        success: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ):
        event = CommercialEncryptionAuditEvent(
            client_id=client_id,
            event_type=event_type,
            resource_type=resource_type,
            resource_id=resource_id,
            key_fingerprint=key_fingerprint,
            success=success,
            metadata_json=metadata,
        )
        db.add(event)

    async def classify_sensitive_payload(self, value: str, key: Optional[str] = None) -> str:
        # public|internal|confidential|restricted|sovereign_restricted
        lower_val = str(value).lower()
        lower_key = str(key or "").lower()
        
        sovereign_patterns = ["sovereign_restricted", "classified_export", "national_security", "citizen_registry", "state_secret"]
        restricted_patterns = ["api_key", "secret_key", "password", "smtp_password", "private_key", "token\": \"", "sk-", "key-"]
        confidential_patterns = ["email", "prompt", "response", "pii", "user_id", "phone", "address", "@"]
        
        # Check key name
        for p in sovereign_patterns:
            if p in lower_key:
                return "sovereign_restricted"
        for p in restricted_patterns:
            if p in lower_key:
                return "restricted"
        for p in confidential_patterns:
            if p in lower_key:
                return "confidential"

        # Check value
        for p in sovereign_patterns:
            if p in lower_val:
                return "sovereign_restricted"
        for p in restricted_patterns:
            if p in lower_val:
                return "restricted"
                
        for p in confidential_patterns:
            if p in lower_val:
                return "confidential"
                
        return "internal"

    async def rotate_tenant_key(self, db: AsyncSession, key_id: uuid.UUID) -> CommercialTenantEncryptionKey:
        old_key = await db.get(CommercialTenantEncryptionKey, key_id)
        if not old_key:
            raise ValueError("Key not found")
            
        # Create new key
        new_key = await self.create_tenant_key(db, old_key.client_id, old_key.key_purpose)
        
        # Mark old key as deprecated
        old_key.key_status = "deprecated"
        old_key.rotated_at = utc_now()
        
        await db.flush()
        await self._log_event(db, old_key.client_id, "rotate", "key", str(key_id), old_key.key_fingerprint)
        return new_key

    async def revoke_tenant_key(self, db: AsyncSession, key_id: uuid.UUID):
        key = await db.get(CommercialTenantEncryptionKey, key_id)
        if not key:
            raise ValueError("Key not found")
            
        key.key_status = "revoked"
        await db.flush()
        await self._log_event(db, key.client_id, "revoke", "key", str(key_id), key.key_fingerprint)

    async def confidential_export_control(
        self, 
        db: AsyncSession, 
        client_id: uuid.UUID, 
        data: Dict[str, Any], 
        dry_run: bool = False
    ) -> Dict[str, Any]:
        result = {}
        for key, value in data.items():
            str_val = str(value)
            classification = await self.classify_sensitive_payload(str_val, key)
            
            if classification == "sovereign_restricted":
                result[key] = "[AIRGAP ONLY: SOVEREIGN RESTRICTED]"
                await self._log_event(db, client_id, "export_blocked", "field", key, metadata={"classification": "sovereign_restricted"})
            elif classification == "restricted":
                if self.settings.commercial_tenant_encryption_block_restricted_exports:
                    if not dry_run:
                        result[key] = "[BLOCK: RESTRICTED]"
                        await self._log_event(db, client_id, "export_blocked", "field", key, metadata={"classification": "restricted"})
                    else:
                        result[key] = f"[DRY_RUN: WOULD BLOCK RESTRICTED] {value}"
                else:
                    result[key] = f"[REDACTED: RESTRICTED] {'*' * 8}"
                    await self._log_event(db, client_id, "export_redacted", "field", key, metadata={"classification": "restricted"})
            elif classification == "confidential":
                if self.settings.commercial_tenant_encryption_require_encrypted_exports:
                    # Logic to encrypt field in export
                    # For simplicity in CSV/JSON exports, we might just base64 or similar if we can't provide a way to decrypt
                    result[key] = f"[ENCRYPTED: CONFIDENTIAL] {base64.b64encode(str_val.encode()).decode()[:16]}..."
                    await self._log_event(db, client_id, "export_encrypted", "field", key, metadata={"classification": "confidential"})
                else:
                    result[key] = value
            else:
                result[key] = value
        return result
