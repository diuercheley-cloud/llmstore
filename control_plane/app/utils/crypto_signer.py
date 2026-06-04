import os

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

# In a real environment, keys would be loaded from a secure vault or HSM.
# For local operations and testing, we generate or load from a local file.
KEY_PATH = ".local_ed25519_key"

def _get_or_create_key() -> ed25519.Ed25519PrivateKey:
    if os.path.exists(KEY_PATH):
        with open(KEY_PATH, "rb") as f:
            return serialization.load_pem_private_key(f.read(), password=None)
    
    private_key = ed25519.Ed25519PrivateKey.generate()
    with open(KEY_PATH, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
    return private_key

_private_key = _get_or_create_key()

def sign_payload(payload: str | bytes) -> str:
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    signature = _private_key.sign(payload)
    return signature.hex()

def verify_signature(payload: str | bytes, signature_hex: str) -> bool:
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    public_key = _private_key.public_key()
    try:
        signature = bytes.fromhex(signature_hex)
        public_key.verify(signature, payload)
        return True
    except Exception:
        return False
