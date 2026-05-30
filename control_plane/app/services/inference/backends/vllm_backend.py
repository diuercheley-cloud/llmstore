import logging
import httpx
from fastapi import HTTPException
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class VllmBackendService:
    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.vllm_base_url
        self.api_key = self.settings.vllm_api_key
        self.timeout = httpx.Timeout(self.settings.vllm_timeout_seconds)

    def _get_client(self) -> httpx.AsyncClient:
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return httpx.AsyncClient(base_url=self.base_url, headers=headers, timeout=self.timeout)

    def check_enabled(self):
        if not self.settings.vllm_backend_enabled:
            raise HTTPException(
                status_code=400,
                detail="vLLM backend is not enabled by feature flag VLLM_BACKEND_ENABLED."
            )

    async def chat_completions(self, payload: dict, stream: bool = False):
        self.check_enabled()
        async with self._get_client() as client:
            endpoint = "/chat/completions"
            # OpenAI compatible endpoint format check
            if not self.base_url.endswith("/v1") and not self.base_url.endswith("/v1/"):
                # fallback or compat
                pass
            
            payload = dict(payload)
            # Ensure model is set
            if "model" not in payload or payload["model"] in ("default", ""):
                payload["model"] = self.settings.vllm_default_model
                
            payload["stream"] = stream
            
            try:
                response = await client.post(endpoint, json=payload)
                response.raise_for_status()
                if stream:
                    # Return streaming iterator
                    return response
                return response.json()
            except httpx.TimeoutException as e:
                logger.error(f"vLLM backend request timed out: {e}")
                raise HTTPException(status_code=504, detail="vLLM request timed out.")
            except httpx.HTTPStatusError as e:
                logger.error(f"vLLM returned HTTP status error: {e}")
                raise HTTPException(status_code=e.response.status_code, detail=f"vLLM backend error: {e.response.text}")
            except Exception as e:
                logger.error(f"Error calling vLLM backend: {e}")
                raise HTTPException(status_code=503, detail="vLLM backend is unavailable.")
