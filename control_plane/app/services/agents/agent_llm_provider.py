# Owner: agent-platform
import abc
import logging
import uuid
import json
from typing import Any, Dict, List, Optional

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

class AgentLLMProvider(abc.ABC):
    @abc.abstractmethod
    async def generate(
        self,
        agent_def: AgentDefinition,
        run: AgentRun,
        allowed_tools: List[str],
        input_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        pass

class MockAgentLLMProvider(AgentLLMProvider):
    """Mock LLM Provider for testing agent executions."""
    def __init__(self, responses: Optional[List[Dict[str, Any]]] = None):
        self.responses = responses or []
        self.current_idx = 0

    async def generate(
        self,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        if self.current_idx < len(self.responses):
            res = self.responses[self.current_idx]
            self.current_idx += 1
            return res
        
        # Default fallback response if no responses left
        return {
            "type": "final",
            "output": "Default mock response",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            "cost_brl": 0.00075
        }

class GatewayAgentLLMProvider(AgentLLMProvider):
    """Real LLM Provider using the internal gateway pipeline."""
    def __init__(self, db: AsyncSession, proxy: InferenceProxy):
        self.db = db
        self.proxy = proxy
        self.settings = get_settings()

    async def generate(
        self,
        agent_def: AgentDefinition,
        run: AgentRun,
        allowed_tools: List[str],
        input_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not self.settings.agent_real_llm_enabled:
            logger.warning("GatewayAgentLLMProvider called but AGENT_REAL_LLM_ENABLED is False. Falling back to mock-like behavior.")
            return {
                "type": "final",
                "output": "[Real LLM disabled] This is a placeholder response.",
                "usage": {"prompt_tokens": 0, "completion_tokens": 0},
                "cost_brl": 0.0
            }

        # 1. Resolve model
        # We need a Client object to satisfy the model_policy API.
        # We'll use the tenant_id to find or simulate a client.
        from app.models.client import Client
        from sqlalchemy import select
        
        try:
            client_uuid = uuid.UUID(run.tenant_id)
            stmt = select(Client).where(Client.id == client_uuid)
        except ValueError:
            # If tenant_id is not a UUID, try matching by name or other logic
            # but usually it should be the Client.id
            stmt = select(Client).where(Client.name == run.tenant_id)
            
        res = await self.db.execute(stmt)
        client = res.scalar_one_or_none()
        
        if not client:
            # Fallback for agents without explicit client records if needed
            # or raise error if isolation is strict.
            raise HTTPException(status_code=403, detail=f"No client found for tenant {run.tenant_id}")

        selected_model, _ = await resolve_requested_model(
            self.db,
            client=client,
            requested_model=agent_def.model_id
        )

        # 2. Plan routing
        routes = plan_routing_order(selected_model, client=client)
        if not routes:
            raise HTTPException(status_code=503, detail="No active backend for agent model")

        # 3. Build payload
        # For agent execution, we typically use chat completion.
        # We need to reconstruct the prompt from run history and agent instructions.
        # For now, let's assume the run.input_hash represents the prompt, 
        # but the real provider needs the full text.
        # The executor should have passed the history or we fetch it here.
        
        # Fetching full prompt history (simplified for now, might need more logic)
        from app.services.agents.agent_memory import AgentMemoryService
        memory_service = AgentMemoryService(self.db)
        history = await memory_service.get_chat_history(run.id) # This method needs to exist or be added
        
        messages = [
            {"role": "system", "content": agent_def.instructions}
        ]
        for h in history:
            messages.append({"role": h["role"], "content": h["content"]})
        
        # Add the current input if not in history
        # (Assuming the first step might not have history yet)
        effective_input = input_override if input_override is not None else run.input_text
        if effective_input and (not history or history[-1].get("content") != effective_input):
            messages.append({"role": "user", "content": effective_input})

        # Since I might not have the raw input in AgentRun, I'll check AgentRun model.
        # If it's missing, I'll have to add it or find where it is stored.
        
        payload = {
            "model": selected_model.model_id,
            "messages": messages,
            "stream": False,
        }
        
        if allowed_tools:
            from app.models.agents import AgentTool
            stmt_tools = select(AgentTool).where(
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

        # 4. Execute via InferenceProxy
        last_exc = None
        effective_plan = resolve_effective_plan(client)
        plan_code = effective_plan.code
        
        for attempt, route in enumerate(routes, start=1):
            backend = route.inference_backend
            if not backend: continue
            
            try:
                backend_url = await resolve_effective_backend_url(self.db, route)
                
                # Quota check
                await ensure_quota(
                    self.db, 
                    client.id, 
                    effective_plan.daily_token_quota,
                    effective_plan.weekly_token_quota,
                    effective_plan.monthly_token_quota,
                    incoming_tokens=0,
                    requests_per_day_limit=effective_plan.requests_per_day
                )
                
                # Proxy call
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
                
                # Parse response
                # ForwardResult.response is a starlette response (JSONResponse or StreamingResponse)
                response_data = forward_result.response.body
                if isinstance(response_data, bytes):
                    response_data = json.loads(response_data)
                
                # 5. Track Usage
                usage = response_data.get("usage", {})
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                
                await record_usage(
                    self.db,
                    client=client,
                    model_id=selected_model.model_id,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                )
                
                from decimal import Decimal
                cost_est = float(estimate_request_cost(
                    monthly_tokens_used_before=0, # Placeholder
                    request_tokens=prompt_tokens + completion_tokens,
                    included_monthly_tokens=effective_plan.monthly_token_quota,
                    overage_price_per_1k_tokens=Decimal(str(effective_plan.overage_price_per_1k_tokens))
                ))

                # 6. Map back to Agent Decision format
                choices = response_data.get("choices", [])
                if not choices:
                    raise HTTPException(status_code=502, detail="Empty choices from LLM")
                    
                choice = choices[0]
                message = choice.get("message", {})
                
                result = {
                    "type": "final",
                    "output": message.get("content", ""),
                    "usage": usage,
                    "cost_brl": cost_est,
                    "backend_id": str(backend.id),
                    "backend_name": backend.name,
                }
                
                if "tool_calls" in message and message["tool_calls"]:
                    tool_call = message["tool_calls"][0]
                    result["type"] = "tool_call"
                    result["tool_name"] = tool_call["function"]["name"]
                    args = tool_call["function"].get("arguments", "{}")
                    if isinstance(args, str):
                        try:
                            result["tool_input"] = json.loads(args)
                        except json.JSONDecodeError:
                            result["tool_input"] = {}
                    else:
                        result["tool_input"] = args

                return result

            except Exception as e:
                logger.exception(f"LLM Gateway call failed on route {route.id} for backend {backend.name}")
                last_exc = e
                continue
        
        raise last_exc or HTTPException(status_code=503, detail="All LLM routes failed")

def get_agent_llm_provider(
    db: AsyncSession,
    proxy: Optional[InferenceProxy] = None,
) -> AgentLLMProvider:
    settings = get_settings()
    if settings.agent_llm_provider == "gateway":
        proxy = proxy or get_inference_proxy()
        return GatewayAgentLLMProvider(db, proxy)
    return MockAgentLLMProvider()
