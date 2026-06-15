import hashlib
import hmac
import secrets


def generate_api_key(prefix: str = "sk-local") -> str:
    return f"{prefix}-{secrets.token_urlsafe(24)}"


def hash_secret(secret: str, salt: str | None = None) -> str:
    secret_salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", secret.encode("utf-8"), secret_salt.encode("utf-8"), 600_000
    )
    return f"{secret_salt}${digest.hex()}"


def verify_secret(secret: str, stored_hash: str) -> bool:
    salt, expected = stored_hash.split("$", 1)
    digest = hashlib.pbkdf2_hmac(
        "sha256", secret.encode("utf-8"), salt.encode("utf-8"), 600_000
    ).hex()
    return hmac.compare_digest(digest, expected)


def short_prefix(secret: str) -> str:
    return secret[:12]
