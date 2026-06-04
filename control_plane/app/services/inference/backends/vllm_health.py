import logging

from app.core.config import get_settings
from app.services.inference.backends.vllm_backend import VllmBackendService

logger = logging.getLogger(__name__)

async def check_vllm_health() -> dict:
    settings = get_settings()
    if not settings.vllm_backend_enabled:
        return {
            "status": "disabled",
            "ok": False,
            "error": "vLLM backend is disabled by feature flag VLLM_BACKEND_ENABLED."
        }

    service = VllmBackendService()
    try:
        async with service._get_client() as client:
            # vLLM exposes /health, or /v1/models can serve as a fallback
            try:
                response = await client.get("/health")
                if response.status_code == 200:
                    return {"status": "healthy", "ok": True}
            except Exception:
                pass
            
            # Fallback to models endpoint to check health
            response = await client.get("/models")
            if response.status_code == 200:
                return {"status": "healthy", "ok": True, "detail": "Fallback check via /models passed"}
            
            return {
                "status": "unhealthy",
                "ok": False,
                "error": f"vLLM responded with status code {response.status_code}"
            }
    except Exception as e:
        logger.error(f"Healthcheck failed for vLLM backend: {e}")
        return {
            "status": "unhealthy",
            "ok": False,
            "error": str(e)
        }
