import json
import logging
from typing import Any

from app.core.config import get_settings
from app.services.provider_settings import is_real_api_key_configured
from app.services.providers.base import ProviderAdapter, ProviderType
from app.services.providers.schemas import ProviderCapabilities
from app.services.providers.errors import ProviderNotConfiguredError

logger = logging.getLogger(__name__)

try:
    import aioboto3
    from botocore.exceptions import ClientError
    HAS_BOTO = True
except ImportError:
    HAS_BOTO = False


class BedrockProvider(ProviderAdapter):
    def __init__(self):
        settings = get_settings()
        self._aws_access_key = settings.aws_access_key_id
        self._aws_secret_key = settings.aws_secret_access_key
        self._region = settings.aws_region or "us-east-1"
        self._timeout = settings.provider_timeout_seconds
        configured = bool(self._aws_access_key and self._aws_secret_key)
        enabled = (
            settings.cloud_providers_enabled
            and settings.bedrock_provider_enabled
            and settings.real_provider_validation_enabled
        )
        super().__init__(
            provider_id="bedrock",
            provider_type=ProviderType.BEDROCK,
            enabled=enabled,
            configured=configured,
        )

    async def _invoke_model(self, model_id: str, body: dict) -> dict:
        if not HAS_BOTO:
            raise RuntimeError("aioboto3 not installed; cannot use Bedrock provider")

        session = aioboto3.Session(
            aws_access_key_id=self._aws_access_key,
            aws_secret_access_key=self._aws_secret_key,
            region_name=self._region,
        )
        async with session.client("bedrock-runtime") as client:
            response = await client.invoke_model(
                modelId=model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(body),
            )
            return json.loads(await response["body"].read())

    async def health_check(self) -> dict[str, Any]:
        if not self.enabled:
            return {"provider_id": "bedrock", "healthy": None, "latency_ms": 0, "error": "disabled"}
        if not self.configured:
            return {"provider_id": "bedrock", "healthy": None, "latency_ms": 0, "error": "not configured"}
        if not HAS_BOTO:
            return {"provider_id": "bedrock", "healthy": False, "latency_ms": 0, "error": "aioboto3 not installed"}
        try:
            session = aioboto3.Session(
                aws_access_key_id=self._aws_access_key,
                aws_secret_access_key=self._aws_secret_key,
                region_name=self._region,
            )
            async with session.client("bedrock") as client:
                await client.list_foundation_models()
                return {"provider_id": "bedrock", "healthy": True, "latency_ms": 0, "error": None}
        except Exception as e:
            return {"provider_id": "bedrock", "healthy": False, "latency_ms": 0, "error": str(e)}

    async def list_models(self) -> list[str]:
        if not self.enabled or not self.configured or not HAS_BOTO:
            return []
        try:
            session = aioboto3.Session(
                aws_access_key_id=self._aws_access_key,
                aws_secret_access_key=self._aws_secret_key,
                region_name=self._region,
            )
            async with session.client("bedrock") as client:
                resp = await client.list_foundation_models()
                return [m["modelId"] for m in resp.get("modelSummaries", [])]
        except Exception:
            logger.warning("bedrock list_models failed")
        return []

    async def chat_completion(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not HAS_BOTO:
            raise RuntimeError("aioboto3 not installed; cannot use Bedrock provider")
        if not self.configured:
            raise ProviderNotConfiguredError("AWS credentials not configured")

        model = payload.get("model", "us.anthropic.claude-3-5-sonnet-20241022-v2:0")
        messages = payload.get("messages", [])

        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": payload.get("max_tokens", 4096),
            "messages": [{"role": m["role"], "content": m["content"]} for m in messages],
        }
        if payload.get("temperature") is not None:
            body["temperature"] = payload["temperature"]
        if payload.get("top_p") is not None:
            body["top_p"] = payload["top_p"]

        raw = await self._invoke_model(model, body)
        return self._to_openai_format(raw, model)

    async def responses(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.chat_completion(payload)

    async def embeddings(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not HAS_BOTO:
            raise RuntimeError("aioboto3 not installed; cannot use Bedrock provider")

        model = payload.get("model", "amazon.titan-embed-text-v2:0")
        input_text = payload.get("input", "")
        if isinstance(input_text, list):
            input_text = input_text[0] if input_text else ""

        body = {"inputText": input_text}
        raw = await self._invoke_model(model, body)

        embedding = raw.get("embedding", raw.get("embeddings", []))
        if embedding and isinstance(embedding, list) and isinstance(embedding[0], list):
            embedding = embedding[0]

        return {
            "object": "list",
            "data": [{"object": "embedding", "embedding": embedding, "index": 0}],
            "model": model,
        }

    def estimate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        return 1.50 * prompt_tokens / 1_000_000 + 7.50 * completion_tokens / 1_000_000

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            chat=True,
            streaming=False,
            responses=True,
            embeddings=True,
            tools=True,
            vision=True,
            json_mode=True,
            max_context_tokens=200000,
            pricing_configured=False,
        )

    @staticmethod
    def _to_openai_format(bedrock_response: dict, model: str) -> dict:
        content = bedrock_response.get("content", [])
        if isinstance(content, list):
            text = " ".join(
                c.get("text", "") if isinstance(c, dict) else str(c)
                for c in content
            )
        else:
            text = str(content)

        usage = bedrock_response.get("usage", {})
        return {
            "id": bedrock_response.get("id", ""),
            "object": "chat.completion",
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": bedrock_response.get("stop_reason", "end_turn"),
            }],
            "model": model,
            "usage": {
                "prompt_tokens": usage.get("input_tokens", 0),
                "completion_tokens": usage.get("output_tokens", 0),
                "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
            },
        }
