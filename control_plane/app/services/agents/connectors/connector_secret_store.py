import logging
from typing import Optional
from cryptography.fernet import Fernet
import os

logger = logging.getLogger(__name__)

class ConnectorSecretStore:
    """
    Handles encryption and decryption of SaaS connector secrets and tokens.
    Uses an encryption key from environment variables.
    """
    def __init__(self):
        # In a real app, this key would be fetched from a secure vault
        key = os.getenv("AGENT_CONNECTOR_ENCRYPTION_KEY")
        if not key:
            # Fallback for dev/test - NEVER use this in production
            logger.warning("AGENT_CONNECTOR_ENCRYPTION_KEY not set, using default for development")
            key = Fernet.generate_key().decode()
        
        self.fernet = Fernet(key.encode())

    def encrypt(self, secret: str) -> bytes:
        return self.fernet.encrypt(secret.encode())

    def decrypt(self, encrypted_secret: bytes) -> str:
        return self.fernet.decrypt(encrypted_secret).decode()

connector_secret_store = ConnectorSecretStore()
