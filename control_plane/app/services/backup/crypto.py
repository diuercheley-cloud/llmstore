import os
import base64
import hashlib
import hmac
import json
from typing import Any
from cryptography.fernet import Fernet
from .errors import BackupCryptoError, BackupKeyError

def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

class BackupCryptoService:
    def __init__(self):
        self._validate_keys()
        self._fernet = Fernet(self._derive_fernet_key())
        self._signing_key = self._derive_signing_key()

    def _validate_keys(self) -> None:
        enc_key = os.getenv("BACKUP_ENCRYPTION_KEY")
        sig_key = os.getenv("BACKUP_SIGNING_KEY")
        if not enc_key or not sig_key:
            raise BackupKeyError(
                "Backup keys configuration error: BACKUP_ENCRYPTION_KEY and BACKUP_SIGNING_KEY "
                "environment variables must be defined."
            )
        if len(enc_key) < 32 or len(sig_key) < 32:
            raise BackupKeyError(
                "Backup keys configuration error: BACKUP_ENCRYPTION_KEY and BACKUP_SIGNING_KEY "
                "must be at least 32 characters long."
            )

    @property
    def key_id(self) -> str:
        env_key_id = os.getenv("BACKUP_KEY_ID")
        if env_key_id:
            return env_key_id
        enc_key = os.getenv("BACKUP_ENCRYPTION_KEY") or ""
        return hashlib.sha256(enc_key.encode("utf-8")).hexdigest()[:16]

    def _derive_fernet_key(self) -> bytes:
        seed = os.getenv("BACKUP_ENCRYPTION_KEY") or ""
        return base64.urlsafe_b64encode(hashlib.sha256(seed.encode("utf-8")).digest())

    def _derive_signing_key(self) -> bytes:
        seed = os.getenv("BACKUP_SIGNING_KEY") or ""
        return seed.encode("utf-8")

    def encrypt(self, data: bytes) -> bytes:
        try:
            return self._fernet.encrypt(data)
        except Exception as e:
            raise BackupCryptoError(f"Encryption failed: {e}")

    def decrypt(self, data: bytes) -> bytes:
        try:
            return self._fernet.decrypt(data)
        except Exception as e:
            raise BackupCryptoError(f"Decryption failed: {e}")

    def sign_payload(self, payload: dict[str, Any]) -> str:
        try:
            return hmac.new(
                self._signing_key, 
                _canonical_json(payload).encode("utf-8"), 
                hashlib.sha256
            ).hexdigest()
        except Exception as e:
            raise BackupCryptoError(f"Signing failed: {e}")

    def verify_signature(self, signature: str, payload: dict[str, Any]) -> bool:
        expected = self.sign_payload(payload)
        return hmac.compare_digest(signature, expected)
