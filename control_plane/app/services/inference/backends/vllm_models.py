import logging

from app.core.config import get_settings
from app.services.inference.backends.vllm_backend import VllmBackendService
from fastapi import HTTPException

logger = logging.getLogger(__name__)

async def list_vllm_models() -> list:
    settings = get_settings()
    if not settings.vllm_backend_enabled:
        return []

    service = VllmBackendService()
    try:
        async with service._get_client() as client:
            response = await client.get("/models")
            if response.status_code == 404:
                # compatibility with OpenAi /v1 prefix
                response = await client.get("/v1/models")
            response.raise_for_status()
            data = response.json()
            # typically {"object": "list", "data": [...]}
            if isinstance(data, dict) and "data" in data:
                return data["data"]
            return data
    except Exception as e:
        logger.error(f"Failed to list models from vLLM backend: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Failed to retrieve models from vLLM backend: {str(e)}"
        )
