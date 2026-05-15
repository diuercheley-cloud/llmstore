# Commercial Routing Policy

## Visão Geral

O **Commercial Routing Policy** é uma camada de decisão que avalia restrições comerciais (plano, saldo, margem, status de faturamento) antes de rotear uma requisição para um provedor de inferência.

Ela funciona como um **wrapper** sobre as estratégias de roteamento existentes (`local_first`, `lowest_cost`, `premium_quality`, `coding`) e adiciona validações financeiras sem quebrar as políticas legadas.

## Ativação

A política comercial é ativada por plano no arquivo `config/customer-pricing.example.json`:

```json
{
  "plans": {
    "basic": {
      "commercial_routing_enabled": true,
      "minimum_margin_percent": 10.0,
      "max_cost_per_request_brl": 0.10,
      "strategy_override": "local_first",
      "cloud_allowed": false
    }
  },
  "commercial_routing": {
    "enabled": false,
    "default_minimum_margin_percent": 5.0,
    "default_max_cost_per_request_brl": 0.50,
    "suspended_plans_allow_local": true,
    "low_balance_threshold_brl": 5.0
  }
}
```

- `commercial_routing.enabled` (global): ativa/desativa a camada inteira.
- `plans.<code>.commercial_routing_enabled`: ativa por plano.
- Se desativada, o roteamento existente (`SmartRouter`) opera normalmente.

## Políticas por Perfil de Cliente

### Basic

| Regra | Comportamento |
|---|---|
| Estratégia | `local_first` |
| Cloud | Bloqueado a menos que `cloud_allowed=true` no plano **e** habilitado no cliente |
| Margem mínima | Se custo estimado ultrapassar margem configurada, provedor é rejeitado |
| Cost cap | `max_cost_per_request_brl` (0.10 BRL) |

### Pro

| Regra | Comportamento |
|---|---|
| Estratégia | `lowest_cost` com fallback |
| Wallet | Respeita saldo disponível |
| Quota | Respeita cotas do plano |
| Cost cap | `max_cost_per_request_brl` (0.50 BRL) |

### Premium (Enterprise)

| Regra | Comportamento |
|---|---|
| Estratégia | `premium_quality` |
| Provedores | Permite provedores melhores (OpenAI, Anthropic) |
| Cost cap | `max_cost_per_request_brl` (`1.00 BRL`) |
| Margem | Respeita margem mínima configurada |

### Coding

| Regra | Comportamento |
|---|---|
| Estratégia | `coding` |
| Preferência | Anthropic > OpenAI > DeepSeek > local |
| Margem negativa | Tenta fallback mais barato antes de bloquear |
| Cost cap | Respeita `max_cost_per_request_brl` do plano |

### Suspenso / Inadimplente

| Regra | Comportamento |
|---|---|
| Cloud | Bloqueado completamente |
| Local | Permitido se `suspended_plans_allow_local=true` |
| Retorno | Rota local selecionada ou erro se nenhuma disponível |

### Saldo Baixo

| Regra | Comportamento |
|---|---|
| Threshold | `low_balance_threshold_brl` (default 5.0 BRL) |
| Preferência | Provedor mais barato / local |
| Cloud | Bloqueado se saldo = 0 e provedor cloud |
| Retorno | Erro claro se nenhuma rota lucrativa/permitida |

## Endpoint de Simulação

### `POST /admin/routing/commercial/simulate`

Simula a decisão comercial **sem executar chamada real a provedor**.

**Input:**
```json
{
  "client_id": "uuid-opcional",
  "plan": "pro",
  "model": "gpt-4",
  "estimated_input_tokens": 500,
  "estimated_output_tokens": 1024,
  "task_type": "general",
  "wallet_balance_brl": 50.0,
  "billing_status": "active",
  "cloud_allowed": true
}
```

**Output:**
```json
{
  "selected_provider": "deepseek",
  "selected_model": "deepseek-model",
  "estimated_cost_brl": 0.0025,
  "estimated_price_brl": 0.015,
  "estimated_margin_brl": 0.0125,
  "estimated_margin_percent": 83.33,
  "policy": "lowest_cost",
  "reason": "pro tier: selected deepseek via lowest_cost",
  "rejected_routes": [
    {
      "provider": "deepseek",
      "model": "deepseek-model",
      "estimated_cost_brl": 0.00025,
      "estimated_price_brl": 0.015,
      "estimated_margin_brl": 0.01475,
      "estimated_margin_percent": 98.33,
      "is_cloud": true,
      "rejected": false,
      "rejection_reason": null
    },
    {
      "provider": "openai",
      "model": "openai-model",
      "estimated_cost_brl": 0.01145,
      "estimated_price_brl": 0.015,
      "estimated_margin_brl": 0.00355,
      "estimated_margin_percent": 23.67,
      "is_cloud": true,
      "rejected": false,
      "rejection_reason": null
    }
  ],
  "tier": "pro"
}
```

## Arquitetura

```
Cliente Request
     |
     v
CommercialRoutingEngine
     |  (avalia plano, saldo, status, margem)
     |
     v
SmartRouter (políticas existentes)
     |  (local_first, lowest_cost, premium_quality, coding)
     |
     v
Provider Selection
```

O `CommercialRoutingEngine` decide **qual estratégia** usar e **quais provedores** são permitidos com base em restrições comerciais. O `SmartRouter` executa a estratégia escolhida.

## Campos de Configuração

### `customer-pricing.json` (por plano)

| Campo | Tipo | Default | Descrição |
|---|---|---|---|
| `commercial_routing_enabled` | bool | false | Ativa camada comercial para este plano |
| `minimum_margin_percent` | float | 5.0 | Margem mínima % para provedores cloud |
| `max_cost_per_request_brl` | float | 0.50 | Custo máximo por requisição em BRL |
| `strategy_override` | string | - | Força estratégia específica |
| `cloud_allowed` | bool | false | Permite roteamento cloud |

### `commercial_routing` (global)

| Campo | Tipo | Default | Descrição |
|---|---|---|---|
| `enabled` | bool | false | Ativa/desativa globalmente |
| `default_minimum_margin_percent` | float | 5.0 | Margem mínima padrão |
| `default_max_cost_per_request_brl` | float | 0.50 | Cost cap padrão |
| `suspended_plans_allow_local` | bool | true | Permite local para suspensos |
| `low_balance_threshold_brl` | float | 5.0 | Threshold para saldo baixo |

## Testes

```bash
pytest tests/test_commercial_routing.py -v
```

Cobre:
- Basic: preferência local, bloqueio cloud, cost cap
- Pro: lowest_cost, wallet balance, max_cost
- Premium: premium_quality, max_cost, provedores premium
- Coding: preferência Anthropic, fallback margem negativa
- Suspenso: bloqueio cloud, permite local
- Saldo baixo: provedor barato, erro sem rota
- Nenhuma chamada real a provedor cloud