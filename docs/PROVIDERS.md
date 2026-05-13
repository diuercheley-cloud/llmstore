# Providers - Multi-Provider Layer

## ProviderAdapter Interface

Cada provider implementa a interface `ProviderAdapter` em `app/services/providers/base.py`:

```python
class ProviderAdapter(ABC):
    provider_id      # unique identifier (e.g. "openai")
    provider_type    # enum: local, lmstudio, openai, anthropic, deepseek, openrouter
    enabled          # bool - whether the provider is active
    configured       # bool - whether API keys/credentials are present

    async health_check()    -> dict
    async list_models()     -> list[str]
    async chat_completion() -> dict
    async responses()       -> dict
    async embeddings()      -> dict
    async estimate_cost()   -> float
    def capabilities()      -> ProviderCapabilities
```

## Provider Registry

Centralizado em `app/services/providers/registry.py`.

Inicializado sob demanda (lazy). Providers são registrados com base em:
- `PROVIDERS_ENABLED` - lista de providers ativos
- `CLOUD_PROVIDERS_ENABLED` - se cloud providers estão habilitados
- Disponibilidade de API keys

### Funções principais:

- `get_providers()` - retorna dict de todos os providers registrados
- `get_provider(provider_id)` - retorna provider específico
- `get_all_provider_statuses()` - status de todos os providers
- `get_all_provider_health()` - health checks assíncronos
- `get_enabled_configured_providers()` - apenas providers prontos para uso

## Capabilities por Provider

### Local (mock)
- chat, streaming, responses, embeddings
- tools: false, vision: false
- max_context: 8192
- pricing: free

### LMStudio
- chat, streaming, embeddings
- responses: false (via proxy)
- tools: se habilitado
- max_context: 4096
- pricing: free (local)

### OpenAI
- chat, streaming, responses, embeddings
- tools: true, vision: true, json_mode: true
- max_context: 128000
- pricing: por modelo (gpt-4o, gpt-4o-mini, etc.)

### Anthropic
- chat, streaming (via Messages API)
- embeddings: false, responses: false (usando chat adapter)
- tools: true, vision: true
- max_context: 200000
- pricing: por modelo (claude-3-*)

### DeepSeek
- chat, streaming, responses, embeddings
- tools: true, json_mode: true
- vision: false
- max_context: 65536
- pricing: por modelo (deepseek-chat, deepseek-reasoner)

### OpenRouter
- chat, streaming, responses (placeholder)
- embeddings: false
- tools: true, vision: true
- max_context: 128000
- pricing: não configurado (futuro)

## Smart Routing

A **Smart Routing Engine** (`app/services/routing/smart_router.py`) integra o provider
registry com heurísticas de roteamento para decidir qual provider usar.

### Arquitetura

```
SmartRouter.route(SmartRouterInput) → RoutingDecision
  ├── Policy Loader (config/routing-policies.example.json)
  ├── Provider Registry (registry.py)
  ├── Cost Estimator
  └── Decision Logger
```

### Integração com Provider Registry

O `SmartRouter` consulta `_is_provider_available()` e `_provider_health()` para
determinar se um provider está pronto para uso. Providers não registrados no
registry são ignorados durante o roteamento.

## Cost Estimation

`estimate_cost(model, prompt_tokens, completion_tokens)` calcula custo estimado
por provider com base em tabelas de preço internas.

Para providers locais, o custo é sempre 0.0.

## Adicionar Novo Provider

1. Criar classe em `app/services/providers/` implementando `ProviderAdapter`
2. Adicionar ao `registry.py` em `_init_registry()`
3. Adicionar env vars em `config.py`
4. Adicionar ao enum `ProviderType` em `base.py`
5. Adicionar documentação
