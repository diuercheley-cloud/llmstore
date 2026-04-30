from app.core.security import generate_api_key, hash_secret, verify_secret


def test_secret_hash_roundtrip():
    api_key = generate_api_key()
    hashed = hash_secret(api_key)
    assert verify_secret(api_key, hashed)
    assert not verify_secret("invalid", hashed)

