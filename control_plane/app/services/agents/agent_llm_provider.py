# Owner: agent-platform
import abc
import logging
import uuid
import json
import time
from typing import Any, Dict, List, Optional
from enum import Enum
from dataclasses import dataclass, field, asdict

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.api.deps import get_inference_proxy
from app.core.config import get_settings
from app.models.agents import AgentDefinition, AgentRun
from app.services.inference_proxy import InferenceProxy, ForwardResult
from app.services.model_policy import (
    resolve_requested_model,
    plan_routing_order,
    resolve_effective_backend_url,
)
from app.services.quota import record_usage, ensure_quota
from app.services.billing import estimate_request_cost, resolve_effective_plan

logger = logging.getLogger(__name__)


class LLMProviderType(str, Enum):
    MOCK = "mock"
    GATEWAY = "gateway"
    REAL = "real"


class ExecutionMode(str, Enum):
    DEVELOPMENT = "development"
    PILOT = "pilot"
    PRODUCTION = "production"


class ProviderResponse(dict):
    """Structured provider response that is also dict-compatible for backward compatibility."""

    _KNOWN_KEYS = [
        "type", "output", "usage", "cost_brl", "provider_type", "model_id",
        "backend_id", "backend_name", "execution_mode", "tokens", "latency",
        "fallback_used", "validation_status", "tool_name", "tool_input",
    ]

    def __init__(
        self,
        type: str = "final",
        output: str = "",
        usage: Optional[Dict[str, int]] = None,
        cost_brl: float = 0.0,
        provider_type: str = "",
        model_id: str = "",
        backend_id: str = "",
        backend_name: str = "",
        execution_mode: str = "",
        tokens: Optional[Dict[str, int]] = None,
        latency: float = 0.0,
        fallback_used: bool = False,
        validation_status: str = "not_validated",
        tool_name: Optional[str] = None,
        tool_input: Optional[Dict[str, Any]] = None,
    ):
        _usage = usage or {"prompt_tokens": 0, "completion_tokens": 0}
        _tokens = tokens or {}
        super().__init__(
            type=type,
            output=output,
            usage=_usage,
            cost_brl=cost_brl,
            provider_type=provider_type,
            model_id=model_id,
            backend_id=backend_id,
            backend_name=backend_name,
            execution_mode=execution_mode,
            tokens=_tokens,
            latency=latency,
            fallback_used=fallback_used,
            validation_status=validation_status,
            tool_name=tool_name,
            tool_input=tool_input,
        )

    def __setitem__(self, key, value):
        super().__setitem__(key, value)

    @property
    def type(self) -> str:
        return self.get("type", "final")

    @property
    def output(self) -> str:
        return self.get("output", "")

    @property
    def usage(self) -> Dict[str, int]:
        return self.get("usage", {"prompt_tokens": 0, "completion_tokens": 0})

    @property
    def cost_brl(self) -> float:
        return self.get("cost_brl", 0.0)

    @property
    def provider_type(self) -> str:
        return self.get("provider_type", "")

    @property
    def model_id(self) -> str:
        return self.get("model_id", "")

    @property
    def backend_id(self) -> str:
        return self.get("backend_id", "")

    @property
    def backend_name(self) -> str:
        return self.get("backend_name", "")

    @property
    def execution_mode(self) -> str:
        return self.get("execution_mode", "")

    @property
    def tokens(self) -> Dict[str, int]:
        return self.get("tokens", {})

    @property
    def latency(self) -> float:
        return self.get("latency", 0.0)

    @property
    def fallback_used(self) -> bool:
        return self.get("fallback_used", False)

    @property
    def validation_status(self) -> str:
        return self.get("validation_status", "not_validated")

    @property
    def tool_name(self) -> Optional[str]:
        return self.get("tool_name")

    @property
    def tool_input(self) -> Optional[Dict[str, Any]]:
        return self.get("tool_input")

    def to_dict(self) -> Dict[str, Any]:
        return dict(self)


class MockProviderError(RuntimeError):
    pass


class ProviderUnavailableError(RuntimeError):
    pass


class AgentLLMProvider(abc.ABC):
    @abc.abstractmethod
    async def generate(
        self,
        agent_def: AgentDefinition,
        run: AgentRun,
        allowed_tools: List[str],
        input_override: Optional[str] = None,
    ) -> ProviderResponse:
        pass

    @property
    @abc.abstractmethod
    def provider_type(self) -> LLMProviderType:
        pass


class MockAgentLLMProvider(AgentLLMProvider):
    """Mock LLM Provider for testing agent executions. NEVER used silently in production."""

    def __init__(self, responses: Optional[List[Dict[str, Any]]] = None):
        self.responses = responses or []
        self.current_idx = 0
        self._provider_type = LLMProviderType.MOCK

    @property
    def provider_type(self) -> LLMProviderType:
        return self._provider_type

    async def generate(
        self,
        agent_def: AgentDefinition,
        run: AgentRun,
        allowed_tools: List[str],
        input_override: Optional[str] = None,
    ) -> ProviderResponse:
        start_time = time.time()

        if self.current_idx < len(self.responses):
            res = self.responses[self.current_idx]
            self.current_idx += 1
        else:
            res = {
                "type": "final",
                "output": "Default mock response",
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
                "cost_brl": 0.00075
            }

        latency = (time.time() - start_time) * 1000
        usage = res.get("usage", {})

        return ProviderResponse(
            type=res.get("type", "final"),
            output=res.get("output", ""),
            usage=usage,
            cost_brl=res.get("cost_brl", 0.0),
            provider_type=LLMProviderType.MOCK.value,
            model_id=agent_def.model_id if agent_def else "mock-model",
            execution_mode=self._detect_execution_mode(),
            tokens={"prompt": usage.get("prompt_tokens", 0), "completion": usage.get("completion_tokens", 0)},
            latency=latency,
            fallback_used=False,
            validation_status="mock_bypass",
            tool_name=res.get("tool_name"),
            tool_input=res.get("tool_input"),
        )

    @staticmethod
    def _detect_execution_mode() -> str:
        settings = get_settings()
        mode = getattr(settings, "deployment_mode", "appliance")
        return mode


class GatewayAgentLLMProvider(AgentLLMProvider):
    """LLM Provider using the internal gateway pipeline."""

    def __init__(self, db: AsyncSession, proxy: InferenceProxy):
        self.db = db
        self.proxy = proxy
        self.settings = get_settings()
        self._provider_type = LLMProviderType.GATEWAY

    @property
    def provider_type(self) -> LLMProviderType:
        return self._provider_type

    async def _resolve_client(self, run: AgentRun):
        from app.models.client import Client
        from sqlalchemy import select

        try:
            client_uuid = uuid.UUID(run.tenant_id)
            stmt = select(Client).where(Client.id == client_uuid)
        except ValueError:
            stmt = select(Client).where(Client.name == run.tenant_id)

        res = await self.db.execute(stmt)
        client = res.scalar_one_or_none()

        if not client:
            raise HTTPException(status_code=403, detail=f"No client found for tenant {run.tenant_id}")
        return client

    async def generate(
        self,
        agent_def: AgentDefinition,
        run: AgentRun,
        allowed_tools: List[str],
        input_override: Optional[str] = None,
    ) -> ProviderResponse:
        start_time = time.time()

        real_llm_enabled = getattr(self.settings, "agent_real_llm_enabled", False)
        if not real_llm_enabled:
            raise ProviderUnavailableError(
                "Gateway LLM provider is selected (AGENT_LLM_PROVIDER=gateway) but "
                "AGENT_REAL_LLM_ENABLED is false. Set AGENT_REAL_LLM_ENABLED=true to enable "
                "real LLM calls, or use AGENT_LLM_PROVIDER=mock for mock execution."
            )

        try:
            client = await self._resolve_client(run)

            selected_model, _ = await resolve_requested_model(
                self.db,
                client=client,
                requested_model=agent_def.model_id
            )

            routes = plan_routing_order(selected_model, client=client)
            if not routes:
                raise ProviderUnavailableError("No active backend for agent model")
        except HTTPException as e:
            raise ProviderUnavailableError(f"Provider unavailable: {e.detail}") from e

        from app.services.agents.agent_memory import AgentMemoryService
        memory_service = AgentMemoryService(self.db)
        history = await memory_service.get_chat_history(run.id)

        messages = [{"role": "system", "content": agent_def.instructions}]
        for h in history:
            messages.append({"role": h["role"], "content": h["content"]})

        effective_input = input_override if input_override is not None else run.input_text
        multimodal_asset_id = getattr(run, "multimodal_asset_id", None)
        
        asset_info = ""
        settings = get_settings()
        if settings.multimodal_enabled and multimodal_asset_id:
            try:
                from app.services.multimodal.asset_store import AssetStore
                from app.services.multimodal.vision_service import VisionService
                from app.services.multimodal.document_vision_service import DocumentVisionService
                from app.services.multimodal.speech_to_text_service import SpeechToTextService

                store = AssetStore(self.db)
                asset = await store.get_asset(multimodal_asset_id, run.tenant_id)
                if asset:
                    if asset.asset_type == "image" and settings.vision_input_enabled:
                        vision = VisionService(self.db)
                        res = await vision.analyze_image(asset.client_id, asset.tenant_id, asset.id, do_ocr=True)
                        asset_info = f"\n[Asset Description: {res.get('description')}][Asset OCR: {res.get('ocr_text')}]"
                    elif asset.asset_type == "document" and settings.document_vision_enabled:
                        doc = DocumentVisionService(self.db)
                        res = await doc.analyze_document(asset.client_id, asset.tenant_id, asset.id)
                        asset_info = f"\n[Document Content: {res.get('extracted_text')}]"
                    elif asset.asset_type == "audio" and settings.speech_to_text_enabled:
                        stt = SpeechToTextService(self.db)
                        res = await stt.transcribe_audio(asset.client_id, asset.tenant_id, asset.id)
                        asset_info = f"\n[Audio Transcription: {res.get('text')}]"
            except Exception as e:
                asset_info = f"\n[Asset Reference Error: {str(e)}]"

        if effective_input and (not history or history[-1].get("content") != effective_input):
            content = effective_input
            if multimodal_asset_id:
                content = f"{content}\n[Asset Reference: {multimodal_asset_id}]{asset_info}"
            messages.append({"role": "user", "content": content})
        elif multimodal_asset_id:
            messages.append({"role": "user", "content": f"[Asset Reference: {multimodal_asset_id}]{asset_info}"})

        payload = {
            "model": selected_model.model_id,
            "messages": messages,
            "stream": False,
        }

        if allowed_tools:
            from app.models.agents import AgentTool
            from sqlalchemy import select as sa_select
            stmt_tools = sa_select(AgentTool).where(
                AgentTool.name.in_(allowed_tools),
                AgentTool.enabled == True
            )
            res_tools = await self.db.execute(stmt_tools)
            db_tools = res_tools.scalars().all()

            if db_tools:
                payload["tools"] = []
                for t in db_tools:
                    schema = t.schema_json
                    if isinstance(schema, str):
                        try:
                            schema = json.loads(schema)
                        except json.JSONDecodeError:
                            schema = {"type": "object", "properties": {}}

                    payload["tools"].append({
                        "type": "function",
                        "function": {
                            "name": t.name,
                            "description": t.description or "",
                            "parameters": schema or {"type": "object", "properties": {}}
                        }
                    })

        last_exc = None
        effective_plan = resolve_effective_plan(client)
        plan_code = effective_plan.code
        fallback_used = False

        for attempt, route in enumerate(routes, start=1):
            backend = route.inference_backend
            if not backend:
                continue

            try:
                backend_url = await resolve_effective_backend_url(self.db, route)

                await ensure_quota(
                    self.db,
                    client.id,
                    effective_plan.daily_token_quota,
                    effective_plan.weekly_token_quota,
                    effective_plan.monthly_token_quota,
                    incoming_tokens=0,
                    requests_per_day_limit=effective_plan.requests_per_day
                )

                forward_result: ForwardResult = await self.proxy.chat(
                    payload=payload,
                    stream=False,
                    include_reasoning=False,
                    backend=backend.provider,
                    backend_url=backend_url,
                    backend_name=backend.name,
                    backend_id=backend.id,
                    prompt_template=selected_model.prompt_template,
                    plan_code=plan_code,
                )

                response_data = forward_result.response.body
                if isinstance(response_data, bytes):
                    response_data = json.loads(response_data)

                usage = response_data.get("usage", {})
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)

                await record_usage(
                    self.db,
                    client_id=client.id,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    token_count_method=usage.get("tokenizer_used"),
                    tokens_estimated=usage.get("fallback_used", True)
                )

                from decimal import Decimal
                cost_est = float(estimate_request_cost(
                    monthly_tokens_used_before=0,
                    request_tokens=prompt_tokens + completion_tokens,
                    included_monthly_tokens=effective_plan.monthly_token_quota,
                    overage_price_per_1k_tokens=Decimal(str(effective_plan.overage_price_per_1k_tokens))
                ))

                choices = response_data.get("choices", [])
                if not choices:
                    raise HTTPException(status_code=502, detail="Empty choices from LLM")

                choice = choices[0]
                message = choice.get("message", {})

                latency = (time.time() - start_time) * 1000

                resp = ProviderResponse(
                    type="final",
                    output=message.get("content", ""),
                    usage=usage,
                    cost_brl=cost_est,
                    provider_type=LLMProviderType.GATEWAY.value,
                    model_id=selected_model.model_id,
                    backend_id=str(backend.id),
                    backend_name=backend.name,
                    execution_mode=getattr(self.settings, "deployment_mode", "appliance"),
                    tokens={"prompt": prompt_tokens, "completion": completion_tokens},
                    latency=latency,
                    fallback_used=fallback_used,
                    validation_status="validated",
                )

                if "tool_calls" in message and message["tool_calls"]:
                    tool_call = message["tool_calls"][0]
                    resp.type = "tool_call"
                    resp.tool_name = tool_call["function"]["name"]
                    args = tool_call["function"].get("arguments", "{}")
                    if isinstance(args, str):
                        try:
                            resp.tool_input = json.loads(args)
                        except json.JSONDecodeError:
                            resp.tool_input = {}
                    else:
                        resp.tool_input = args

                return resp

            except Exception as e:
                logger.exception(f"LLM Gateway call failed on route {route.id} for backend {backend.name}")
                last_exc = e
                fallback_used = True
                continue

        raise last_exc or ProviderUnavailableError("All LLM routes failed")


class RealAgentLLMProvider(AgentLLMProvider):
    """Direct external LLM provider. Skips the internal gateway for direct provider calls."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self._provider_type = LLMProviderType.REAL

    @property
    def provider_type(self) -> LLMProviderType:
        return self._provider_type

    async def generate(
        self,
        agent_def: AgentDefinition,
        run: AgentRun,
        allowed_tools: List[str],
        input_override: Optional[str] = None,
    ) -> ProviderResponse:
        start_time = time.time()

        proxy = get_inference_proxy()
        gateway = GatewayAgentLLMProvider(self.db, proxy)
        result = await gateway.generate(agent_def, run, allowed_tools, input_override)
        result["provider_type"] = LLMProviderType.REAL.value
        result["validation_status"] = "real_provider"
        result["latency"] = (time.time() - start_time) * 1000
        return result


def get_deployment_mode() -> str:
    settings = get_settings()
    return getattr(settings, "deployment_mode", "appliance")


def validate_provider_for_mode(provider_type: LLMProviderType, deployment_mode: str) -> None:
    settings = get_settings()

    if provider_type == LLMProviderType.MOCK:
        if deployment_mode in ("production", "enterprise_managed"):
            allow_mock = getattr(settings, "agent_allow_mock_llm_in_production", False)
            if not allow_mock:
                raise MockProviderError(
                    f"Mock LLM provider is not allowed in deployment mode '{deployment_mode}'. "
                    f"Set AGENT_ALLOW_MOCK_LLM_IN_PRODUCTION=true to override (NOT RECOMMENDED)."
                )
            logger.warning(
                "Mock LLM provider used in production mode with explicit override. "
                "This should NOT be used for GA workloads."
            )
        elif deployment_mode == "pilot":
            logger.warning(
                "Mock LLM provider used in pilot mode. "
                "Use AGENT_LLM_PROVIDER=gateway or AGENT_LLM_PROVIDER=real for pilot evaluation."
            )

    if provider_type in (LLMProviderType.GATEWAY, LLMProviderType.REAL):
        require_real = getattr(settings, "agent_require_real_llm_for_production", True)
        if deployment_mode in ("production", "enterprise_managed") and not require_real:
            logger.warning(
                f"AGENT_REQUIRE_REAL_LLM_FOR_PRODUCTION is set to false in '{deployment_mode}' mode. "
                f"This weakens the production readiness posture."
            )


def get_agent_llm_provider(
    db: AsyncSession,
    proxy: Optional[InferenceProxy] = None,
) -> AgentLLMProvider:
    settings = get_settings()
    provider_str = getattr(settings, "agent_llm_provider", "mock")
    deployment_mode = get_deployment_mode()

    try:
        provider_type = LLMProviderType(provider_str)
    except ValueError:
        raise ValueError(
            f"Invalid AGENT_LLM_PROVIDER='{provider_str}'. "
            f"Must be one of: {[e.value for e in LLMProviderType]}"
        )

    validate_provider_for_mode(provider_type, deployment_mode)

    if provider_type == LLMProviderType.MOCK:
        return MockAgentLLMProvider()

    if provider_type == LLMProviderType.GATEWAY:
        proxy = proxy or get_inference_proxy()
        return GatewayAgentLLMProvider(db, proxy)

    if provider_type == LLMProviderType.REAL:
        return RealAgentLLMProvider(db)

    raise ValueError(f"Unhandled provider type: {provider_type}")
