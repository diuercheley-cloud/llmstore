import uuid
from typing import Any, Dict, Optional

from app.models.commercial_crypto_trust import CommercialSigningProfile, CryptoOperationType
from app.services.security.crypto_provider_registry import CryptoProviderRegistry
from app.services.security.kms_runtime import KMSRuntime, KMSRuntimeError
from sqlalchemy.orm import Session


class SigningServiceError(Exception):
    pass


class SigningService:
    def __init__(self, db: Session):
        self.db = db
        self.kms_runtime = KMSRuntime(db)

    def get_signing_profile(self, profile_id: uuid.UUID) -> CommercialSigningProfile:
        profile = self.db.query(CommercialSigningProfile).filter(CommercialSigningProfile.id == profile_id).first()
        if not profile:
            raise SigningServiceError(f"Signing profile {profile_id} not found.")
        return profile

    async def sign_payload(self, profile_id: uuid.UUID, payload: bytes, context: Optional[Dict[str, Any]] = None) -> bytes:
        try:
            profile = self.get_signing_profile(profile_id)
            key_material = self.kms_runtime.get_key_material(profile.key_id)
            provider_config = self.kms_runtime.get_provider_config(key_material.provider_id)
            
            provider = CryptoProviderRegistry.get_provider(provider_config.provider_type)
            
            signature = await provider.sign(payload, key_material.encrypted_key_blob, profile.algorithm)
            
            self.kms_runtime.log_operation(profile.key_id, CryptoOperationType.SIGN, "success", context or {})
            return signature
        except KMSRuntimeError as e:
            raise SigningServiceError(str(e))
        except Exception as e:
            # We log failed signing in the kms runtime explicitly here if we got the key
            raise SigningServiceError(f"Signing failed: {e}")

    async def verify_signature(self, profile_id: uuid.UUID, payload: bytes, signature: bytes, context: Optional[Dict[str, Any]] = None) -> bool:
        try:
            profile = self.get_signing_profile(profile_id)
            key_material = self.kms_runtime.get_key_material(profile.key_id)
            provider_config = self.kms_runtime.get_provider_config(key_material.provider_id)
            
            provider = CryptoProviderRegistry.get_provider(provider_config.provider_type)
            
            is_valid = await provider.verify(payload, signature, key_material.encrypted_key_blob, profile.algorithm)
            
            self.kms_runtime.log_operation(profile.key_id, CryptoOperationType.VERIFY, "success" if is_valid else "invalid", context or {})
            return is_valid
        except Exception as e:
            raise SigningServiceError(f"Signature verification failed: {e}")
