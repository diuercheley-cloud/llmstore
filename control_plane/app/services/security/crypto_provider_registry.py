import abc
from typing import Any, Dict

from app.models.commercial.commercial_crypto_trust import CryptoProviderType


class CryptoProviderInterface(abc.ABC):
    @abc.abstractmethod
    async def encrypt(self, plaintext: bytes, key_material: Any) -> bytes:
        pass

    @abc.abstractmethod
    async def decrypt(self, ciphertext: bytes, key_material: Any) -> bytes:
        pass

    @abc.abstractmethod
    async def sign(self, payload: bytes, key_material: Any, algorithm: str) -> bytes:
        pass

    @abc.abstractmethod
    async def verify(self, payload: bytes, signature: bytes, key_material: Any, algorithm: str) -> bool:
        pass
        
    @abc.abstractmethod
    async def generate_key(self, key_type: str) -> Any:
        pass


class LocalKeystoreProvider(CryptoProviderInterface):
    # This is a basic implementation of a local keystore. In a real scenario, this would use a secure local storage.
    async def encrypt(self, plaintext: bytes, key_material: Any) -> bytes:
        # Placeholder for local encryption logic
        return b"ENC:" + plaintext

    async def decrypt(self, ciphertext: bytes, key_material: Any) -> bytes:
        if ciphertext.startswith(b"ENC:"):
            return ciphertext[4:]
        return ciphertext

    async def sign(self, payload: bytes, key_material: Any, algorithm: str) -> bytes:
        # Placeholder for signing
        return b"SIG:" + payload

    async def verify(self, payload: bytes, signature: bytes, key_material: Any, algorithm: str) -> bool:
        return signature == b"SIG:" + payload

    async def generate_key(self, key_type: str) -> Any:
        return {"type": key_type, "material": "local_mock_material"}


class VaultPlaceholderProvider(CryptoProviderInterface):
    async def encrypt(self, plaintext: bytes, key_material: Any) -> bytes:
        return b"VAULT_ENC:" + plaintext

    async def decrypt(self, ciphertext: bytes, key_material: Any) -> bytes:
        if ciphertext.startswith(b"VAULT_ENC:"):
            return ciphertext[10:]
        return ciphertext

    async def sign(self, payload: bytes, key_material: Any, algorithm: str) -> bytes:
        return b"VAULT_SIG:" + payload

    async def verify(self, payload: bytes, signature: bytes, key_material: Any, algorithm: str) -> bool:
        return signature == b"VAULT_SIG:" + payload

    async def generate_key(self, key_type: str) -> Any:
        return {"type": key_type, "material": "vault_reference_id"}


class HSMPlaceholderProvider(CryptoProviderInterface):
    async def encrypt(self, plaintext: bytes, key_material: Any) -> bytes:
        return b"HSM_ENC:" + plaintext

    async def decrypt(self, ciphertext: bytes, key_material: Any) -> bytes:
        if ciphertext.startswith(b"HSM_ENC:"):
            return ciphertext[8:]
        return ciphertext

    async def sign(self, payload: bytes, key_material: Any, algorithm: str) -> bytes:
        return b"HSM_SIG:" + payload

    async def verify(self, payload: bytes, signature: bytes, key_material: Any, algorithm: str) -> bool:
        return signature == b"HSM_SIG:" + payload

    async def generate_key(self, key_type: str) -> Any:
        return {"type": key_type, "material": "hsm_slot_id"}


class SovereignOfflineProvider(CryptoProviderInterface):
    async def encrypt(self, plaintext: bytes, key_material: Any) -> bytes:
        return b"OFFLINE_ENC:" + plaintext

    async def decrypt(self, ciphertext: bytes, key_material: Any) -> bytes:
        if ciphertext.startswith(b"OFFLINE_ENC:"):
            return ciphertext[12:]
        return ciphertext

    async def sign(self, payload: bytes, key_material: Any, algorithm: str) -> bytes:
        return b"OFFLINE_SIG:" + payload

    async def verify(self, payload: bytes, signature: bytes, key_material: Any, algorithm: str) -> bool:
        return signature == b"OFFLINE_SIG:" + payload

    async def generate_key(self, key_type: str) -> Any:
        return {"type": key_type, "material": "offline_encrypted_blob"}


class CryptoProviderRegistry:
    _providers: Dict[CryptoProviderType, CryptoProviderInterface] = {
        CryptoProviderType.LOCAL_KEYSTORE: LocalKeystoreProvider(),
        CryptoProviderType.VAULT: VaultPlaceholderProvider(),
        CryptoProviderType.HSM: HSMPlaceholderProvider(),
        CryptoProviderType.SOVEREIGN_OFFLINE: SovereignOfflineProvider(),
    }

    @classmethod
    def get_provider(cls, provider_type: CryptoProviderType) -> CryptoProviderInterface:
        if provider_type not in cls._providers:
            raise ValueError(f"Provider type {provider_type} not registered.")
        return cls._providers[provider_type]

    @classmethod
    def register_provider(cls, provider_type: CryptoProviderType, provider: CryptoProviderInterface):
        cls._providers[provider_type] = provider
