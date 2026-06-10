---
owner: platform-ops
status: consolidated
---

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
- **Configuração:**
  - `LMSTUDIO_ENABLED=true` (padrão: false)
  - `LMSTUDIO_BASE_URL=http://192.168.101.1:1234/v1`
  - `LMSTUDIO_CHAT_MODEL=nvidia/nemotron-3-nano-4b`
  - `LMSTUDIO_API_KEY=lm-studio` (opcional/mock)
  - `LMSTUDIO_TIMEOUT=60`
- **Teste Real Local:**
  - Para executar um teste real de integração local, use o comando:
    ```bash
    LM_STUDIO_BASE_URL=http://192.168.101.1:1234/v1 LM_STUDIO_MODEL=nvidia/nemotron-3-nano-4b pytest -m local_llm tests/integration/test_lmstudio_real.py
    ```
  - Este teste será pulado automaticamente no CI ou caso as variáveis de ambiente necessárias não estejam configuradas.

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

## Real Provider Validation (v1.8.1)

Para validar providers reais com segurança:

- Chaves vão **APENAS** em `.env.local` (nunca em `.env.example`)
- Provider precisa de `*_PROVIDER_ENABLED=true` + `REAL_PROVIDER_VALIDATION_ENABLED=true`
- O helper `scripts/dev/lib/real-provider-env.sh` provê funções seguras de validação
- O script `scripts/validators/validate-real-provider-env-local.sh` verifica ambiente completo
- Testes em `tests/test_real_provider_env*.py` (sem dependência de internet)

### OpenAI Real Provider

O adapter OpenAI (`openai_provider.py`) agora verifica **três guards** antes de ativar:
1. `CLOUD_PROVIDERS_ENABLED=true` (global)
2. `OPENAI_PROVIDER_ENABLED=true` (específico OpenAI)
3. `REAL_PROVIDER_VALIDATION_ENABLED=true` (gatekeeper global)

Validação dedicada:

```bash
# Dry-run (sem custo)
make validate-openai-real-dry

# Real (com chamadas reais)
make validate-openai-real
```

### DeepSeek Real Provider

O adapter DeepSeek (`deepseek_provider.py`) verifica **três guards** antes de ativar:
1. `CLOUD_PROVIDERS_ENABLED=true` (global)
2. `DEEPSEEK_PROVIDER_ENABLED=true` (específico DeepSeek)
3. `REAL_PROVIDER_VALIDATION_ENABLED=true` (gatekeeper global)

DeepSeek não implementa Responses API nem Embeddings API — `capabilities.responses=False`,
`capabilities.embeddings=False`. Esses métodos retornam `NotImplementedError`.

Validação dedicada:

```bash
# Dry-run (sem custo)
make validate-deepseek-real-dry

# Real (com chamadas reais)
make validate-deepseek-real
```

### Anthropic

O adapter Anthropic (`anthropic_provider.py`) verifica **três guards** antes de ativar:
1. `CLOUD_PROVIDERS_ENABLED=true` (global)
2. `ANTHROPIC_PROVIDER_ENABLED=true` (específico Anthropic)
3. `REAL_PROVIDER_VALIDATION_ENABLED=true` (gatekeeper global)

Anthropic não implementa Responses API nem Embeddings API — `capabilities.responses=False`,
`capabilities.embeddings=False`. Esses métodos retornam `NotImplementedError`.

O adapter mapeia automaticamente o formato interno de mensagens para a **Messages API**:
- System prompt (`role=system`) → parâmetro `system` separado
- Content blocks com `image_url` → `image` blocks em base64
- Usage: `input_tokens`/`output_tokens` → `prompt_tokens`/`completion_tokens`

Validação dedicada:

```bash
# Dry-run (sem custo)
make validate-anthropic-real-dry

# Real (com chamadas reais)
make validate-anthropic-real
```

Documentação completa: [REAL_PROVIDER_VALIDATION.md](REAL_PROVIDER_VALIDATION.md)

### Real Provider Cost Validation (v1.8.1)

O script `scripts/dev/measure-real-provider-costs.sh` mede custo real/estimado:

```bash
# Dry-run (sem custo)
make measure-provider-costs-dry

# Real (custo real mínimo por provider)
make measure-provider-costs
```

Gera relatório por provider com: custo USD, custo BRL, preço cliente, lucro bruto e margem.
Resultados em `artifacts/real-provider-validation/costs/<timestamp>/`.

Endpoint: `GET /admin/providers/cost-validation/latest`

## Cost Validation
Providers costs are verified via `make measure-provider-costs`. This script ensures margins and limits are respected.
