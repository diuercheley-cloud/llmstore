# Billing BRL - v1.8.0

## Visão Geral

O **Billing BRL** adiciona contabilidade financeira por request à plataforma híbrida
local + cloud. Cada requisição registra:

- Custo do provider (USD/BRL)
- Preço cobrado do cliente (BRL)
- Margem bruta
- Lucro/prejuízo por request

## Arquitetura

```
Request → Pricing Engine → RequestFinancial (DB)
              │
              ├── Provider Pricing (config/provider-pricing.example.json)
              ├── Customer Pricing (config/customer-pricing.example.json)
              ├── FX Rate (USD_BRL_RATE env var)
              └── Margin Calculator
```

## Tabela: request_financials

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | UUID | PK |
| client_id | UUID FK | Cliente |
| api_key_prefix | string | Prefixo da chave |
| endpoint_type | string | chat, responses, embeddings, rag, tts |
| provider | string | local, openai, anthropic, etc. |
| model | string | Modelo usado |
| requested_model | string | Modelo solicitado |
| resolved_model | string | Modelo resolvido |
| prompt_tokens | int | Tokens de prompt |
| completion_tokens | int | Tokens de completion |
| total_tokens | int | Soma |
| cache_hit | bool | Se houve cache hit |
| latency_ms | int | Latência |
| provider_cost_usd | numeric | Custo do provider em USD |
| provider_cost_brl | numeric | Custo do provider em BRL |
| customer_price_brl | numeric | Preço cobrado do cliente |
| gross_profit_brl | numeric | Lucro bruto |
| margin_percent | numeric | Margem percentual |
| fx_rate | numeric | Taxa de câmbio |
| fx_rate_source | string | manual_env (default) |
| pricing_rule_id | string | Regra de preço aplicada |
| created_at | timestamp | Data de criação |

## Config Provider Pricing

`config/provider-pricing.example.json`:

```json
{
  "fx_rate_brl_per_usd": 5.00,
  "providers": {
    "local": { "cost_usd_per_1k_prompt": 0.0, "pricing_configured": true },
    "openai": { "cost_usd_per_1k_prompt": 0.0025, "pricing_configured": false }
  }
}
```

## Config Customer Pricing

`config/customer-pricing.example.json`:

```json
{
  "plans": {
    "basic": { "markup_percent": 50, "price_brl_per_1k_prompt": 0.02 },
    "pro": { "markup_percent": 40, "cloud_allowed": true }
  },
  "cache_discount_percent": 50
}
```

## Pricing Engine

`control_plane/app/services/billing/pricing_engine.py`

### Funções

| Função | Descrição |
|--------|-----------|
| `estimate_provider_cost()` | Custo do provider em USD/BRL |
| `calculate_customer_price()` | Preço do cliente por plano |
| `calculate_margin()` | Margem bruta |
| `convert_usd_to_brl()` | Conversão cambial |
| `record_request_financials()` | Persiste no banco |
| `calculate_financials()` | Tudo em um (simulação) |

### FX Rate

- Default: `USD_BRL_RATE=5.00`
- Não busca câmbio externo por padrão
- Source registrado como `manual_env`

## Planos

| Plano | Markup | Cloud Allowed | Max Cost/Request |
|-------|--------|---------------|-----------------|
| Free | 0% | false | R$ 0.00 |
| Basic | 50% | false | R$ 0.10 |
| Pro | 40% | true | R$ 0.50 |
| Enterprise | 30% | true | R$ 1.00 |

## Cache Discount

Quando `cache_hit=true`, o preço do cliente é reduzido em
`cache_discount_percent` (default: 50%).

## Endpoints Admin

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | /admin/billing/provider-costs | Lista custos dos providers |
| GET | /admin/billing/margins/summary | Resumo de margens por provider |
| GET | /admin/billing/usage-financials | Registros financeiros |
| POST | /admin/billing/pricing/simulate | Simular precificação |
| GET | /admin/hybrid/financials | Custos, receita e margem consolidados (hybrid) |
| GET | /admin/hybrid/summary | Overview financeiro da plataforma híbrida |

Protegidos por admin token (`X-Admin-Token`).

## Hybrid Admin Dashboard

O Admin Dashboard exibe cards financeiros no contexto da plataforma híbrida:

- **Revenue & Margin** — Receita, custo provider, margem por provider (admin apenas)
- **Provider Costs** — Custos configurados USD/1K tokens

Clientes **nunca** veem `provider_cost_brl` ou `margin_percent` no portal.

## Exemplo de Simulação

```bash
curl -X POST http://localhost:8080/admin/billing/pricing/simulate \
  -H "X-Admin-Token: seu-token" \
  -H "Content-Type: application/json" \
  -d '{"provider":"local","prompt_tokens":1000,"completion_tokens":500,"plan_code":"basic"}'
```

Resposta:
```json
{
  "provider": "local",
  "plan_code": "basic",
  "provider_cost_usd": 0.0,
  "provider_cost_brl": 0.0,
  "customer_price_brl": 0.03,
  "gross_profit_brl": 0.03,
  "margin_percent": 100.0,
  "pricing_configured": true,
  "fx_rate": 5.0,
  "fx_rate_source": "manual_env"
}
```

## Prepaid Wallet (v1.8.0)

A plataforma agora conta com **carteira pré-paga em BRL** com ledger contábil local/manual.

### Fluxo

1. Admin credita saldo do cliente via `POST /admin/billing/wallets/{client_id}/manual-credit`
2. Cliente utiliza a API — o custo é debitado automaticamente
3. Se saldo insuficiente, o roteamento para cloud é bloqueado
4. Cliente acompanha saldo e transações no portal (`GET /portal/wallet`)

### Tabelas

- `ai_wallets`: saldo BRL por cliente (1:1)
- `ai_wallet_transactions`: ledger append-only de todas as movimentações

### Serviço

`control_plane/app/services/billing/wallet_service.py`

### Documentação

Consulte [PREPAID_WALLET_BRL.md](PREPAID_WALLET_BRL.md) para detalhes completos.

## Intelligent Cache Billing (v1.8.0)

O Intelligent Cache integra-se ao billing:

- `cache_hit=true` no `RequestFinancial`
- `provider_cost_brl=0.0` quando cache hit (sem chamada ao backend)
- `customer_price_brl` reduzido conforme `cache_discount_percent` na política do tenant
- Margem calculada normalmente (100% quando custo provider é zero)

### Configuração de Desconto

No `config/customer-pricing.example.json`:
```json
{
  "cache_discount_percent": 50,
  "plans": {
    "pro": {
      "price_brl_per_1k_prompt": 0.05,
      "price_brl_per_1k_completion": 0.15
    }
  }
}
```

Cache hits pagam 50% do valor normal por padrão. Pode ser sobrescrito por política do tenant.

## Segurança

- Nenhuma chamada externa para câmbio por padrão
- Preços são configuráveis, nunca expostos em logs de debug
- Cliente vê apenas `customer_price_brl`, nunca `provider_cost_brl` ou `margin_percent`
- Admin vê margem completa
- Sem integração de cobrança real (PIX) nesta etapa
- Sem dados bancários armazenados
