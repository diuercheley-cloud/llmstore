import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx
from app.services.inference.backends.base import Capability, InferenceBackendBase

logger = logging.getLogger(__name__)


class OpenAICompatibleBackend(InferenceBackendBase):
    def __init__(self, name: str, base_url: str, api_key: str | None = None):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.headers = {}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"
        self.client = httpx.AsyncClient(base_url=self.base_url, headers=self.headers, timeout=60.0)

    async def health(self) -> bool:
        try:
            # Common health check for OpenAI-compatible APIs
            response = await self.client.get("/v1/models")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check failed for {self.name}: {e}")
            return False

    async def list_models(self) -> list[str]:
        try:
            response = await self.client.get("/v1/models")
            if response.status_code == 200:
                data = response.json()
                return [m["id"] for m in data.get("data", [])]
            return []
        except Exception as e:
            logger.error(f"List models failed for {self.name}: {e}")
            return []

    async def infer_chat(
        self, model: str, messages: list[dict[str, Any]], stream: bool = False, **kwargs
    ) -> Any | AsyncIterator[Any]:
        payload = {"model": model, "messages": messages, "stream": stream, **kwargs}

        if stream:
            return self._stream_request("/v1/chat/completions", payload)
        else:
            response = await self.client.post("/v1/chat/completions", json=payload)
            response.raise_for_status()
            return response.json()

    async def infer_completion(
        self, model: str, prompt: str, stream: bool = False, **kwargs
    ) -> Any | AsyncIterator[Any]:
        payload = {"model": model, "prompt": prompt, "stream": stream, **kwargs}

        if stream:
            return self._stream_request("/v1/completions", payload)
        else:
            response = await self.client.post("/v1/completions", json=payload)
            response.raise_for_status()
            return response.json()

    async def infer_embeddings(
        self, model: str, input: str | list[str], **kwargs
    ) -> list[list[float]]:
        payload = {"model": model, "input": input, **kwargs}
        response = await self.client.post("/v1/embeddings", json=payload)
        response.raise_for_status()
        data = response.json()
        return [item["embedding"] for item in data.get("data", [])]

    def supports_capability(self, capability: Capability) -> bool:
        # OpenAI compatible backends generally support these
        supported = {
            Capability.TEXT,
            Capability.CHAT,
            Capability.EMBEDDINGS,
            Capability.STREAMING,
            Capability.TOOL_CALLING,
        }
        return capability in supported

    async def _stream_request(self, path: str, payload: dict[str, Any]) -> AsyncIterator[Any]:
        async with self.client.stream("POST", path, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        yield json.loads(data)
                    except json.JSONDecodeError:
                        continue

    async def close(self):
        await self.client.aclose()
