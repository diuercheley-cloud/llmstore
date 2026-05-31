"""
Secrets Manager integration for agent credentials.
Supports HashiCorp Vault and AWS Secrets Manager backends.
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class SecretsBackend(ABC):
    @abstractmethod
    async def get_secret(self, path: str, key: Optional[str] = None) -> Optional[str]: ...

    @abstractmethod
    async def set_secret(self, path: str, value: Any, key: Optional[str] = None) -> bool: ...

    @abstractmethod
    async def delete_secret(self, path: str) -> bool: ...

    @abstractmethod
    async def list_secrets(self, prefix: str) -> List[str]: ...


class VaultBackend(SecretsBackend):
    """
    HashiCorp Vault KV v2 backend.
    Requires VAULT_ADDR, VAULT_TOKEN env vars.
    """

    def __init__(self):
        self.settings = get_settings()
        self.addr = self.settings.vault_addr or "http://localhost:8200"
        self.token = self.settings.vault_token or ""
        self.mount = self.settings.vault_kv_mount or "secret"
        self._http = httpx.AsyncClient(
            base_url=self.addr,
            headers={"X-Vault-Token": self.token},
            timeout=10.0,
        )

    async def get_secret(self, path: str, key: Optional[str] = None) -> Optional[str]:
        try:
            resp = await self._http.get(f"/v1/{self.mount}/data/{path}")
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            data = resp.json().get("data", {}).get("data", {})
            if key:
                return data.get(key)
            return json.dumps(data)
        except Exception as e:
            logger.error("Vault get_secret failed for %s: %s", path, e)
            return None

    async def set_secret(self, path: str, value: Any, key: Optional[str] = None) -> bool:
        data = {key: value} if key else (value if isinstance(value, dict) else {"value": value})
        try:
            resp = await self._http.post(
                f"/v1/{self.mount}/data/{path}",
                json={"data": data},
            )
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.error("Vault set_secret failed for %s: %s", path, e)
            return False

    async def delete_secret(self, path: str) -> bool:
        try:
            resp = await self._http.delete(f"/v1/{self.mount}/metadata/{path}")
            return resp.is_success
        except Exception:
            return False

    async def list_secrets(self, prefix: str) -> List[str]:
        try:
            resp = await self._http.get(f"/v1/{self.mount}/metadata/{prefix}", params={"list": "true"})
            if resp.status_code == 404:
                return []
            resp.raise_for_status()
            keys = resp.json().get("data", {}).get("keys", [])
            return [f"{prefix}/{k}" for k in keys]
        except Exception as e:
            logger.error("Vault list_secrets failed for %s: %s", prefix, e)
            return []

    async def close(self):
        await self._http.aclose()


class AWSSecretsManagerBackend(SecretsBackend):
    """
    AWS Secrets Manager backend.
    Uses boto3 under the hood.
    """

    def __init__(self):
        self.settings = get_settings()
        self.region = self.settings.aws_region or "us-east-1"
        self._client = None

    async def _get_client(self):
        if self._client is None:
            import aioboto3
            session = aioboto3.Session()
            self._client = await session.client(
                "secretsmanager",
                region_name=self.region,
            ).__aenter__()
        return self._client

    async def get_secret(self, path: str, key: Optional[str] = None) -> Optional[str]:
        try:
            client = await self._get_client()
            resp = await client.get_secret_value(SecretId=path)
            secret = resp.get("SecretString", "")
            if key and secret:
                parsed = json.loads(secret)
                return parsed.get(key)
            return secret
        except Exception as e:
            logger.error("AWS Secrets Manager get failed for %s: %s", path, e)
            return None

    async def set_secret(self, path: str, value: Any, key: Optional[str] = None) -> bool:
        try:
            client = await self._get_client()
            secret_value = json.dumps({key: value}) if key else (json.dumps(value) if not isinstance(value, str) else value)
            await client.create_secret(Name=path, SecretString=secret_value)
            return True
        except Exception as e:
            logger.error("AWS Secrets Manager set failed for %s: %s", path, e)
            return False

    async def delete_secret(self, path: str) -> bool:
        try:
            client = await self._get_client()
            await client.delete_secret(SecretId=path, ForceDeleteWithoutRecovery=True)
            return True
        except Exception:
            return False

    async def list_secrets(self, prefix: str) -> List[str]:
        try:
            client = await self._get_client()
            paginator = client.get_paginator("list_secrets")
            results = []
            async for page in paginator.paginate(Filters=[{"Key": "name", "Values": [prefix]}]):
                for secret in page.get("SecretList", []):
                    results.append(secret["Name"])
            return results
        except Exception as e:
            logger.error("AWS Secrets Manager list failed: %s", e)
            return []


class SecretsManagerService:
    """
    Unified secrets manager that routes to the configured backend.
    """

    def __init__(self):
        self.settings = get_settings()
        self._backend: Optional[SecretsBackend] = None

    def _get_backend(self) -> SecretsBackend:
        if self._backend is not None:
            return self._backend

        provider = self.settings.secrets_manager_provider or "vault"
        if provider == "vault":
            self._backend = VaultBackend()
        elif provider == "aws":
            self._backend = AWSSecretsManagerBackend()
        else:
            raise ValueError(f"Unknown secrets manager provider: {provider}")
        return self._backend

    async def get_agent_credential(self, agent_id: str, credential_name: str) -> Optional[str]:
        backend = self._get_backend()
        path = f"agents/{agent_id}/credentials"
        return await backend.get_secret(path, key=credential_name)

    async def set_agent_credential(self, agent_id: str, credential_name: str, value: str) -> bool:
        backend = self._get_backend()
        path = f"agents/{agent_id}/credentials"
        return await backend.set_secret(path, value, key=credential_name)

    async def delete_agent_credentials(self, agent_id: str) -> bool:
        backend = self._get_backend()
        path = f"agents/{agent_id}/credentials"
        return await backend.delete_secret(path)

    async def get_provider_api_key(self, provider: str) -> Optional[str]:
        backend = self._get_backend()
        path = "providers/api-keys"
        return await backend.get_secret(path, key=provider)

    async def set_provider_api_key(self, provider: str, api_key: str) -> bool:
        backend = self._get_backend()
        path = "providers/api-keys"
        return await backend.set_secret(path, api_key, key=provider)

    async def get_tenant_secret(self, tenant_id: str, key: str) -> Optional[str]:
        backend = self._get_backend()
        path = f"tenants/{tenant_id}/secrets"
        return await backend.get_secret(path, key=key)

    async def list_agent_secrets(self, agent_id: str) -> List[str]:
        backend = self._get_backend()
        path = f"agents/{agent_id}/credentials"
        return await backend.list_secrets(path)
