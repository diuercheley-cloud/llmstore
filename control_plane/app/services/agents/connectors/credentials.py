# Owner: agent-platform
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class CredentialManager:
    """
    Manages SaaS credentials, ensuring they are not leaked and handling different auth flows.
    """

    @staticmethod
    def get_credentials(
        tenant_id: str, connector_name: str, credential_id: str | None = None
    ) -> dict[str, Any]:
        """
        Retrieves credentials for a given tenant and connector.
        Supports environment variables for development.
        """
        # 1. Check for manual tokens in environment variables (DEV ONLY)
        env_key = f"AGENT_CONNECTOR_{connector_name.upper()}_TOKEN"
        env_token = os.getenv(env_key)
        if env_token:
            return {
                "token": env_token,
                "type": "manual_env",
                "scopes": ["repo", "user", "read", "write"],
            }

        # 2. Fetch from DB if id provided
        if credential_id:
            # Simple sync wrapper for demo, in real app this would be async
            # For this prototype, we'll return empty if not found easily
            return {}

        return {}

    @staticmethod
    def validate_scope(required_scopes: list, provided_scopes: list) -> bool:
        return all(scope in provided_scopes for scope in required_scopes)

    @staticmethod
    def prepare_oauth_flow(tenant_id: str, connector_name: str) -> dict[str, Any]:
        """
        Prepares the state for an OAuth flow.
        """
        from app.core.config import get_settings

        if not get_settings().agent_connector_oauth_enabled:
            raise PermissionError("OAuth flow is currently disabled.")

        # Implementation of OAuth initiation would go here
        return {
            "status": "oauth_initiated",
            "auth_url": f"https://auth.{connector_name}.com/oauth/authorize",
            "state": "random_state_string",
        }


credential_manager = CredentialManager()
