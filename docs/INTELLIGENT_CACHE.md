# Intelligent Cache

## Visão Geral

O Intelligent Cache reduz custos de inferência armazenando respostas anteriores e reutilizando-as para requests idênticas ou semanticamente similares.

## Cache Exato

- Mesma request normalizada retorna mesma resposta
- TTL configurável (default: 3600s)
- Chave: hash SHA256 do payload normalizado
- Headers: `x-cache: HIT/MISS/BYPASS`, `x-cache-type: exact/semantic/none`

## Cache Semântico

- **Disabled por padrão** (`SEMANTIC_CACHE_ENABLED=false`)
- Usa embedding determinístico local (mock)
- Threshold de similaridade configurável (default: 0.85)
- `client_id` obrigatório no filtro
- Não retorna para tasks não idempotentes

## Configuração

| Variável | Default | Descrição |
|----------|---------|-----------|
| `RESPONSE_CACHE_ENABLED` | `true` | Habilita cache exato |
| `RESPONSE_CACHE_TTL_SECONDS` | `3600` | TTL padrão |
| `SEMANTIC_CACHE_ENABLED` | `false` | Habilita cache semântico |

## Políticas por Tenant

- `cache_enabled`
- `semantic_cache_enabled`
- `cache_ttl`
- `cache_sensitive_data_allowed`
- `cache_price_discount_percent`

## Admin Endpoints

- `GET /admin/cache/stats`
- `GET /admin/cache/entries?client_id=...`
- `POST /admin/cache/invalidate`
- `GET /admin/cache/policies`
- `GET /admin/hybrid/cache` — Estatísticas no contexto da plataforma híbrida

O card **Cache Stats** no Admin Dashboard exibe:
- Status do cache exato e semântico (ON/OFF)
- TTL configurado
- Número de hits e entries

## Billing

- `cache_hit=true` em usage
- `provider_cost_brl=0` em hit
- `customer_price_brl` reduzido conforme política de desconto
