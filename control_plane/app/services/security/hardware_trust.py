import abc
import hashlib
from typing import Any, Dict

from app.core.config import get_settings


class HardwareTrustProvider(abc.ABC):
    @abc.abstractmethod
    def get_measurements(self) -> Dict[str, Any]:
        pass

    @abc.abstractmethod
    def sign_quote(self, nonce: bytes) -> bytes:
        pass

    @abc.abstractmethod
    def verify_quote(self, quote: bytes, nonce: bytes) -> bool:
        pass


class MockHardwareTrustProvider(HardwareTrustProvider):
    def get_measurements(self) -> Dict[str, Any]:
        return {
            "pcr0": "0000000000000000000000000000000000000000000000000000000000000000",
            "status": "mock_trusted"
        }

    def sign_quote(self, nonce: bytes) -> bytes:
        # Mock signature
        return hashlib.sha256(b"mock_quote" + nonce).digest()

    def verify_quote(self, quote: bytes, nonce: bytes) -> bool:
        return quote == self.sign_quote(nonce)


class FileBasedHardwareTrustProvider(HardwareTrustProvider):
    def get_measurements(self) -> Dict[str, Any]:
        return {
            "pcr0": "file_based_trusted",
            "status": "file_trusted"
        }

    def sign_quote(self, nonce: bytes) -> bytes:
        return hashlib.sha256(b"file_quote" + nonce).digest()

    def verify_quote(self, quote: bytes, nonce: bytes) -> bool:
        return quote == self.sign_quote(nonce)


def get_hardware_trust_provider() -> HardwareTrustProvider:
    settings = get_settings()
    if not settings.hardware_trust_enabled:
        return MockHardwareTrustProvider()
        
    if settings.hardware_trust_provider == "file":
        return FileBasedHardwareTrustProvider()
    
    # Default to mock
    return MockHardwareTrustProvider()
