# Smart Routing Engine - v1.8.0

## Visão Geral

A **Smart Routing Engine** é o cérebro de roteamento híbrido local + cloud do `llm-inference-stack`.
Ela decide qual provider e modelo usar para cada requisição com base em:

- Estratégia configurada (local-first, lowest-cost, premium-quality, etc.)
- Disponibilidade do provider (health checks, circuit breaker)
- Políticas de tenant (quota, saldo, orçamento)
- Preferências de latência e custo

## Arquitetura

```
Request → Smart Router → RoutingDecision
            │
            ├── Policy Loader (config/routing-policies.example.json)
            ├── Provider Registry (registry.py)
            ├── Cost Estimator
            └── Decision Logger
```

## Service

`control_plane/app/services/routing/smart_router.py`

Classe `SmartRouter` com método `route(SmartRouterInput) -> RoutingDecision`.

## Schemas

`control_plane/app/schemas/routing.py`

### SmartRouterInput

| Campo | Tipo | Default | Descrição |
|-------|------|---------|-----------|
| tenant | str | None | Identificador do tenant |
| client_id | UUID | None | ID do cliente |
| endpoint_type | EndpointType | chat | chat/responses/embeddings/rag/tts |
| requested_model | str | None | Modelo solicitado |
| task_type | TaskType | None | general/coding/summarization/rag/embedding |
| prompt_estimated_tokens | int | 0 | Tokens estimados do prompt |
| max_output_tokens | int | 512 | Máximo de tokens de saída |
| plan | str | None | Nome do plano |
| remaining_quota | int | None | Quota restante |
| wallet_balance_brl | float | None | Saldo da carteira |
| cloud_allowed | bool | False | Se cloud é permitido |
| latency_preference | str | None | Preferência de latência |
| budget_preference | str | None | Preferência de orçamento |
| strategy | RoutingStrategy | local_first | Estratégia de roteamento |

### RoutingDecision

| Campo | Tipo | Descrição |
|-------|------|-----------|
| selected_provider | str | Provider escolhido |
| selected_model | str | Modelo escolhido |
| selected_backend | str | Backend selecionado |
| reason | str | Motivo da decisão (sanitizado) |
| fallback_chain | list[str] | Cadeia de fallback |
| estimated_cost_brl | float | Custo estimado em BRL |
| policy_applied | str | Estratégia aplicada |
| cloud_used | bool | Se cloud foi usado |
| warnings | list[str] | Avisos |

## Estratégias

| Estratégia | Prioridade | Descrição |
|-----------|-----------|-----------|
| local_first | Local | Tenta local providers primeiro, fallback para mock |
| lowest_cost | Custo | Menor custo primeiro (deepseek, local, lmstudio) |
| premium_quality | Qualidade | Melhor qualidade (openai, anthropic) |
| coding | Código | Prefere anthropic para tarefas de código |
| embeddings_optimized | Embeddings | Otimizado para embeddings |
| rag_optimized | RAG | Otimizado para RAG |
| fallback_only | Fallback | Apenas fallback chain |

## Heurísticas

1. **cloud_allowed=false**: somente local/lmstudio/mock
2. **task_type=coding + Anthropic configurado**: Anthropic
3. **low_budget + DeepSeek configurado**: DeepSeek
4. **premium_quality + OpenAI configurado**: OpenAI
5. **Provider down**: próximo fallback
6. **Saldo insuficiente**: local-only
7. **Modelo solicitado existe**: respeitar

## Endpoints Admin

| Método | Path | Descrição |
|--------|------|-----------|
| POST | /admin/routing/simulate | Simular decisão de roteamento |
| GET | /admin/routing/policies | Listar políticas configuradas |
| GET | /admin/routing/last-decisions | Últimas decisões |

Protegidos por admin token (`X-Admin-Token`).

## Config Policy

Arquivo `config/routing-policies.example.json`:

```json
{
  "default_strategy": "local_first",
  "allow_cloud_fallback": false,
  "complexity_threshold": 4000,
  "coding_provider_preference": "anthropic",
  "low_budget_provider_preference": "deepseek",
  "premium_provider_preference": "openai",
  "max_provider_cost_per_request_brl": 0.50,
  "tenant_policy_overrides": {},
  "fallback_order": ["local", "lmstudio", "mock"]
}
```

## Segurança

- Decisões nunca contêm prompts ou mensagens do usuário
- API keys e secrets são redactados dos logs de decisão
- Razões sanitizadas (máx 500 chars, sem quebras de linha)
- Cloud providers disabled por padrão
- Prompt consciente: nunca enviar dados sensíveis para cloud sem autorização

## Exemplo de Requisição

```bash
curl -X POST http://localhost:8080/admin/routing/simulate \
  -H "X-Admin-Token: seu-token" \
  -H "Content-Type: application/json" \
  -d '{
    "endpoint_type": "chat",
    "requested_model": "gemma",
    "task_type": "general",
    "cloud_allowed": false,
    "strategy": "local_first",
    "prompt_estimated_tokens": 500
  }'
```

## Exemplo de Resposta

```json
{
  "decision": {
    "selected_provider": "local",
    "selected_model": "local-model",
    "selected_backend": "local",
    "reason": "local_first strategy: selected local",
    "fallback_chain": ["local"],
    "estimated_cost_brl": 0.0,
    "policy_applied": "local_first",
    "cloud_used": false,
    "warnings": []
  },
  "strategies_considered": [
    "local_first", "lowest_cost", "premium_quality",
    "coding", "embeddings_optimized", "rag_optimized",
    "fallback_only"
  ],
  "provider_states": {
    "local": "unknown_async",
    "lmstudio": "unknown_async",
    "openai": "unregistered",
    "anthropic": "unregistered",
    "deepseek": "unregistered",
    "openrouter": "unregistered",
    "mock": "unknown_async"
  },
  "config_snapshot": {
    "default_strategy": "local_first",
    "allow_cloud_fallback": false,
    "cloud_providers_enabled": false,
    "fallback_order": ["local", "lmstudio", "mock"]
  }
}
```
