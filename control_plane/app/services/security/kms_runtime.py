import uuid
from typing import Any

from app.models.commercial.commercial_crypto_trust import (
    CommercialCryptoOperation,
    CommercialKeyMaterial,
    CommercialKMSProvider,
    CryptoOperationType,
    KeyUsageStatus,
)
from app.services.security.crypto_provider_registry import CryptoProviderRegistry
from sqlalchemy.orm import Session


class KMSRuntimeError(Exception):
    pass


class KMSRuntime:
    def __init__(self, db: Session):
        self.db = db

    def get_provider_config(self, provider_id: uuid.UUID) -> CommercialKMSProvider:
        provider = (
            self.db.query(CommercialKMSProvider)
            .filter(CommercialKMSProvider.id == provider_id)
            .first()
        )
        if not provider:
            raise KMSRuntimeError(f"Provider {provider_id} not found.")
        if not provider.is_active:
            raise KMSRuntimeError(f"Provider {provider_id} is not active.")
        return provider

    def get_key_material(self, key_id: uuid.UUID) -> CommercialKeyMaterial:
        key = (
            self.db.query(CommercialKeyMaterial).filter(CommercialKeyMaterial.id == key_id).first()
        )
        if not key:
            raise KMSRuntimeError(f"Key {key_id} not found.")
        if key.status != KeyUsageStatus.ACTIVE:
            raise KMSRuntimeError(f"Key {key_id} is not active. Current status: {key.status}")
        return key

    def log_operation(
        self, key_id: uuid.UUID, op_type: CryptoOperationType, status: str, audit_context: dict
    ):
        op_log = CommercialCryptoOperation(
            key_id=key_id, operation_type=op_type, status=status, audit_context=audit_context
        )
        self.db.add(op_log)
        self.db.commit()

    async def encrypt(
        self, key_id: uuid.UUID, plaintext: bytes, context: dict[str, Any] | None = None
    ) -> bytes:
        try:
            key_material = self.get_key_material(key_id)
            provider_config = self.get_provider_config(key_material.provider_id)

            provider = CryptoProviderRegistry.get_provider(provider_config.provider_type)

            # The actual material passed would depend on the implementation
            # In our placeholder, it's just the db record or its blob
            ciphertext = await provider.encrypt(plaintext, key_material.encrypted_key_blob)

            self.log_operation(key_id, CryptoOperationType.ENCRYPT, "success", context or {})
            return ciphertext
        except Exception as e:
            self.log_operation(
                key_id, CryptoOperationType.ENCRYPT, "failed", {"error": str(e), **(context or {})}
            )
            raise KMSRuntimeError(f"Encryption failed: {e}")

    async def decrypt(
        self, key_id: uuid.UUID, ciphertext: bytes, context: dict[str, Any] | None = None
    ) -> bytes:
        try:
            key_material = self.get_key_material(key_id)
            provider_config = self.get_provider_config(key_material.provider_id)

            provider = CryptoProviderRegistry.get_provider(provider_config.provider_type)

            plaintext = await provider.decrypt(ciphertext, key_material.encrypted_key_blob)

            self.log_operation(key_id, CryptoOperationType.DECRYPT, "success", context or {})
            return plaintext
        except Exception as e:
            self.log_operation(
                key_id, CryptoOperationType.DECRYPT, "failed", {"error": str(e), **(context or {})}
            )
            raise KMSRuntimeError(f"Decryption failed: {e}")
