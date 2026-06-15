import pytest
from app.services.backup.crypto import BackupCryptoService
from app.services.backup.errors import BackupCryptoError


def test_crypto_service_init_fails_no_keys(monkeypatch):
    monkeypatch.delenv("BACKUP_ENCRYPTION_KEY", raising=False)
    monkeypatch.delenv("BACKUP_SIGNING_KEY", raising=False)
    with pytest.raises(BackupCryptoError):
        BackupCryptoService()


def test_crypto_service_encrypt_decrypt(monkeypatch):
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", "a" * 32)
    monkeypatch.setenv("BACKUP_SIGNING_KEY", "b" * 32)
    crypto = BackupCryptoService()

    data = b"hello world"
    encrypted = crypto.encrypt(data)
    assert encrypted != data

    decrypted = crypto.decrypt(encrypted)
    assert decrypted == data


def test_crypto_service_signing(monkeypatch):
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", "a" * 32)
    monkeypatch.setenv("BACKUP_SIGNING_KEY", "b" * 32)
    crypto = BackupCryptoService()

    payload = {"foo": "bar"}
    signature = crypto.sign_payload(payload)
    assert isinstance(signature, str)

    assert crypto.verify_signature(signature, payload) is True
    assert crypto.verify_signature(signature, {"foo": "baz"}) is False
