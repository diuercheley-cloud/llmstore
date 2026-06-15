from __future__ import annotations

import hashlib
import hmac

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM as _AESGCM  # type: ignore
except Exception:  # pragma: no cover
    _AESGCM = None


class AESGCM:
    def __init__(self, key: bytes):
        self.key = key
        self._impl = _AESGCM(key) if _AESGCM is not None else None

    def encrypt(self, nonce: bytes, data: bytes, associated_data: bytes | None) -> bytes:
        if self._impl is not None:
            return self._impl.encrypt(nonce, data, associated_data)

        keystream = _expand_keystream(self.key, nonce, len(data))
        ciphertext = bytes(a ^ b for a, b in zip(data, keystream))
        tag = hmac.new(
            self.key, nonce + (associated_data or b"") + ciphertext, hashlib.sha256
        ).digest()[:16]
        return ciphertext + tag

    def decrypt(self, nonce: bytes, data: bytes, associated_data: bytes | None) -> bytes:
        if self._impl is not None:
            return self._impl.decrypt(nonce, data, associated_data)

        ciphertext, tag = data[:-16], data[-16:]
        expected = hmac.new(
            self.key, nonce + (associated_data or b"") + ciphertext, hashlib.sha256
        ).digest()[:16]
        if not hmac.compare_digest(tag, expected):
            raise ValueError("invalid authentication tag")
        keystream = _expand_keystream(self.key, nonce, len(ciphertext))
        return bytes(a ^ b for a, b in zip(ciphertext, keystream))


def _expand_keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    blocks: list[bytes] = []
    counter = 0
    while sum(len(block) for block in blocks) < length:
        blocks.append(hmac.new(key, nonce + counter.to_bytes(4, "big"), hashlib.sha256).digest())
        counter += 1
    return b"".join(blocks)[:length]
