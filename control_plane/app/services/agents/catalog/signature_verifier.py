import hashlib
import logging

logger = logging.getLogger(__name__)

try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa

    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False


class SignatureVerifier:
    """
    Verifies cryptographic signatures on agent catalog items.
    Supports ECDSA (primary) and RSA (fallback) signatures.
    Gracefully degrades when cryptography library is unavailable.
    """

    SUPPORTED_ALGORITHMS = {"ecdsa-p256", "rsa-sha256"}

    @staticmethod
    def verify_signature(
        data: str,
        signature: str,
        public_key: str,
        algorithm: str = "ecdsa-p256",
    ) -> bool:
        if not signature or not public_key or not data:
            return False

        if not HAS_CRYPTOGRAPHY:
            logger.warning("cryptography library not installed; signature verification degraded")
            return _degraded_verify(data, signature, public_key)

        try:
            if algorithm == "ecdsa-p256":
                return _verify_ecdsa(data, signature, public_key)
            elif algorithm == "rsa-sha256":
                return _verify_rsa(data, signature, public_key)
            else:
                logger.warning(f"Unsupported signature algorithm: {algorithm}")
                return False
        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False

    @staticmethod
    def sign_data(data: str, private_key: str, algorithm: str = "ecdsa-p256") -> str | None:
        if not HAS_CRYPTOGRAPHY:
            logger.warning("cryptography library not installed; cannot sign")
            return None

        try:
            if algorithm == "ecdsa-p256":
                key = serialization.load_pem_private_key(private_key.encode(), password=None)
                if not isinstance(key, ec.EllipticCurvePrivateKey):
                    raise ValueError("Key is not an EC private key")
                sig = key.sign(data.encode(), ec.ECDSA(hashes.SHA256()))
                return sig.hex()
            elif algorithm == "rsa-sha256":
                key = serialization.load_pem_private_key(private_key.encode(), password=None)
                if not isinstance(key, rsa.RSAPrivateKey):
                    raise ValueError("Key is not an RSA private key")
                sig = key.sign(data.encode(), padding.PKCS1v15(), hashes.SHA256())
                return sig.hex()
            else:
                logger.warning(f"Unsupported signing algorithm: {algorithm}")
                return None
        except Exception as e:
            logger.error(f"Signing failed: {e}")
            return None


def _verify_ecdsa(data: str, signature_hex: str, public_key_pem: str) -> bool:
    try:
        sig = bytes.fromhex(signature_hex)
        pub_key = serialization.load_pem_public_key(public_key_pem.encode())
        if not isinstance(pub_key, ec.EllipticCurvePublicKey):
            return False
        pub_key.verify(sig, data.encode(), ec.ECDSA(hashes.SHA256()))
        return True
    except InvalidSignature:
        return False


def _verify_rsa(data: str, signature_hex: str, public_key_pem: str) -> bool:
    try:
        sig = bytes.fromhex(signature_hex)
        pub_key = serialization.load_pem_public_key(public_key_pem.encode())
        if not isinstance(pub_key, rsa.RSAPublicKey):
            return False
        pub_key.verify(sig, data.encode(), padding.PKCS1v15(), hashes.SHA256())
        return True
    except InvalidSignature:
        return False


def _degraded_verify(data: str, signature: str, public_key: str) -> bool:
    """Fallback verification using SHA-256 hash comparison when cryptography is unavailable."""
    expected = hashlib.sha256((data + public_key).encode()).hexdigest()
    return signature == expected[: len(signature)] if len(signature) <= 64 else False
