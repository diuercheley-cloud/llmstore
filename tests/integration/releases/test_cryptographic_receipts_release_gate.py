import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "control_plane"))

from app.services.inference.cryptographic_receipts import (
    _make_timestamp_token,
    get_signing_key,
    sign_payload,
    verify_payload_signature,
)


def test_sign_and_verify_receipt():
    # Key default path setup for tests
    key_path = "config/receipts_private_key_test.pem"
    if os.path.exists(key_path):
        try:
            os.remove(key_path)
        except Exception:
            pass

    with patch.dict(
        os.environ,
        {
            "CRYPTO_RECEIPTS_PRIVATE_KEY_PATH": key_path,
            "CRYPTO_RECEIPTS_REQUIRE_SIGNATURE": "false",
        },
    ):
        payload = "my-test-payload-hash-123"
        signature = sign_payload(payload)
        assert len(signature) > 0

        # Verify
        assert verify_payload_signature(payload, signature) is True

        # Tampered payload fails
        assert verify_payload_signature(payload + "altered", signature) is False


def test_missing_key_blocks_when_required():
    key_path = "config/receipts_private_key_missing.pem"
    if os.path.exists(key_path):
        try:
            os.remove(key_path)
        except Exception:
            pass

    with patch.dict(
        os.environ,
        {"CRYPTO_RECEIPTS_PRIVATE_KEY_PATH": key_path, "CRYPTO_RECEIPTS_REQUIRE_SIGNATURE": "true"},
    ):
        with pytest.raises(ValueError, match="Signing key is missing"):
            get_signing_key()


def test_external_timestamp_disabled_no_placeholder():
    with patch.dict(os.environ, {"CRYPTO_RECEIPTS_EXTERNAL_TIMESTAMP_ENABLED": "false"}):
        mode, token = _make_timestamp_token("local", "hash123")
        assert mode == "local"
        assert "placeholder" not in token
