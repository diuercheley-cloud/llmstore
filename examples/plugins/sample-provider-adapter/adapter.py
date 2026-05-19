"""Sample provider adapter plugin.

This plugin implements the PluginContract interface to adapt
a hypothetical external inference provider.
"""

from typing import Optional


class SampleProviderAdapter:
    """Adapter for the SampleProvider API."""

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self.api_key = self.config.get("api_key", "")
        self.base_url = self.config.get(
            "base_url", "https://api.sample-provider.example.com/v1"
        )

    async def chat_completion(self, messages: list[dict], **kwargs) -> dict:
        """Send a chat completion request to the provider."""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": kwargs.get("model", "default"),
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 1024),
        }
        # In a real adapter, this would make an HTTP request:
        # async with httpx.AsyncClient() as client:
        #     resp = await client.post(f"{self.base_url}/chat", json=payload, headers=headers)
        #     return resp.json()
        return {
            "id": "sample-123",
            "object": "chat.completion",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": f"Simulated response from {self.base_url}",
                    },
                }
            ],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
        }

    async def health_check(self) -> dict:
        """Check provider connectivity."""
        return {"status": "ok", "provider": "sample"}


def create_plugin(config: Optional[dict] = None) -> SampleProviderAdapter:
    """Factory function called by the plugin loader."""
    return SampleProviderAdapter(config)
