import pytest
from app.services.operations.adapter_registry.hash_utils import (
    canonical_json,
    sha256_hex,
    compute_registry_hash,
)

class TestAdapterRegistryHashUtils:
    def test_canonical_json_ordering(self):
        data1 = {"a": 1, "b": 2}
        data2 = {"b": 2, "a": 1}
        assert canonical_json(data1) == canonical_json(data2)

    def test_sha256_hex(self):
        data = "test"
        # sha256("test") = 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08
        expected = "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
        assert sha256_hex(data) == expected

    def test_compute_registry_hash_deterministic(self):
        payload = {"client_id": "123", "adapter_name": "test"}
        hash1 = compute_registry_hash(payload)
        hash2 = compute_registry_hash(payload)
        assert hash1 == hash2
        assert len(hash1) == 64
