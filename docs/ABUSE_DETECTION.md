# Abuse Detection

## Visão Geral

Sistema de detecção de abuso para proteger custos, provedores cloud e recursos locais.

## Sinais Monitorados

| Sinal | Severidade | Janela | Gatilho |
|-------|-----------|--------|---------|
| `requests_per_minute_above_plan` | medium | 60s | Requests/min > plano |
| `tokens_per_minute_above_plan` | medium | 60s | Tokens/min > cota |
| `repeated_auth_errors` | high | 300s | 5+ erros 401/403 |
| `repeated_giant_prompts` | medium | 900s | 3+ mesmo prompt gigante |
| `request_loop` | low | 600s | 5+ mesma request exata |
| `high_cache_miss_repetitive` | low | 600s | 10+ cache misses repetitivos |
| `cloud_without_balance` | high | 60s | Request cloud sem saldo |
| `high_estimated_cost` | high | 300s | Custo > R$ 5 em curto período |
| `repeated_streaming_abort` | low | 300s | 3+ streaming abortado |
| `excessive_rag_upload` | medium | 300s | 5+ uploads RAG em 5min |
| `excessive_tts_chars` | medium | 60s | Chars TTS > limite mensal |

## Ações

| Ação | Descrição |
|------|-----------|
| `log_only` | Apenas registra o evento |
| `warn` | Retorna header de aviso |
| `throttle` | Reduz velocidade (não bloqueia) |
| `require_captcha_placeholder` | Retorna desafio captcha |
| `suspend_api_key` | Revoga chave de API |
| `suspend_client` | Bloqueia o cliente |

## Configuração

```env
ABUSE_DETECTION_ENABLED=true
ABUSE_AUTO_SUSPEND_ENABLED=false
ABUSE_DRY_RUN=true
```

- `ABUSE_DETECTION_ENABLED`: Liga/desliga detecção
- `ABUSE_AUTO_SUSPEND_ENABLED`: Suspensão automática (desligada por padrão)
- `ABUSE_DRY_RUN`: Modo seguro - registra eventos mas não bloqueia

## Admin Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/admin/security/abuse/events` | Lista eventos com filtros |
| GET | `/admin/security/abuse/summary` | Sumário agregado |
| POST | `/admin/security/abuse/actions/{id}/ack` | Reconhecer ação |
| POST | `/admin/security/abuse/clients/{id}/suspend` | Suspender cliente |
| POST | `/admin/security/abuse/clients/{id}/unsuspend` | Reativar cliente |

## Segurança

- Nenhum prompt completo é logado
- Nenhuma API key é exposta
- Modo dry-run não afeta clientes reais
- Depende apenas de Redis (contadores) e PostgreSQL (eventos)
- Sem dependência de cloud
- Sem carga pesada de processamento

## Validação

```bash
make validate-hybrid-abuse
# ou
./scripts/validate-hybrid-abuse-detection-local.sh
```
