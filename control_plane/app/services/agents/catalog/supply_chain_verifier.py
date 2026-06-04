import hashlib


class SupplyChainVerifier:
    @staticmethod
    def verify_checksum(content: bytes, expected_checksum: str) -> bool:
        actual = hashlib.sha256(content).hexdigest()
        return actual == expected_checksum
