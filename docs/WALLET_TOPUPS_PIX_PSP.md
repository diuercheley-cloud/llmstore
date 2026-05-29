---
owner: platform-ops
status: consolidated
---

# Wallet Top-ups via PSP/PIX

## Objetivo

Este modulo adiciona recarga opcional de wallet por adapter de pagamento, sem transformar o billing core em gateway financeiro.

O comportamento padrao continua local/offline:

- `PAYMENT_PROVIDER=disabled`
- `PAYMENT_REAL_ENABLED=false`
- Nenhum PSP real e chamado por acidente
- O mock PSP pode ser ativado em testes locais com `PAYMENT_PROVIDER=mock`

## Arquitetura

Camadas:

- `billing-core`: continua responsavel por wallet, saldo e ledger append-only.
- `payment_adapters`: cria intencoes de pagamento e normaliza webhooks.
- `payment_topups`: persiste intents/eventos, valida idempotencia e credita wallet.
- API portal/webhook: apenas orquestra entrada HTTP.

Tabelas:

- `wallet_topup_intents`: intencao criada pelo cliente no portal.
- `payment_webhook_events`: evento recebido do provider, com resumo sanitizado.
- `ai_wallet_transactions`: ledger final do credito, usando `type=future_pix_credit`.

## Variaveis de Ambiente

```env
# Default seguro: sem PSP
PAYMENT_PROVIDER=disabled
PAYMENT_REAL_ENABLED=false
PAYMENT_WEBHOOK_SECRET=

# Teste local com PSP mock
PAYMENT_PROVIDER=mock

# Placeholder para PSP real
PAYMENT_PROVIDER=nome_do_psp
PAYMENT_REAL_ENABLED=true
PAYMENT_WEBHOOK_SECRET=use-um-segredo-fora-do-git
```

`PAYMENT_REAL_ENABLED=false` bloqueia qualquer provider diferente de `mock` ou `disabled`.

## Endpoints

### Criar recarga

```bash
curl -s -X POST http://localhost:8080/portal/wallet/topups \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "amount_brl": "100.00",
    "idempotency_key": "cliente-123-topup-001"
  }'
```

Resposta mock:

```json
{
  "amount_brl": 100.0,
  "status": "pending",
  "provider": "mock",
  "external_id": "mock_topup_...",
  "idempotency_key": "cliente-123-topup-001",
  "payment_data": {
    "mode": "mock",
    "pix_copy_paste": "MOCK-PIX-...",
    "qr_code_text": "mock pix ...",
    "expires_in_seconds": 1800
  }
}
```

### Listar recargas do cliente

```bash
curl -s http://localhost:8080/portal/wallet/topups \
  -H "Authorization: Bearer $API_KEY"
```

O cliente ve apenas as proprias recargas.

### Webhook

```bash
curl -s -X POST http://localhost:8080/payments/webhooks/mock \
  -H "Content-Type: application/json" \
  -d '{
    "external_id": "mock_topup_abc",
    "idempotency_key": "cliente-123-topup-001",
    "amount_brl": "100.00",
    "status": "paid"
  }'
```

Com `PAYMENT_WEBHOOK_SECRET` configurado, envie:

```text
X-Payment-Signature: <hex hmac-sha256 do body bruto>
```

## Idempotencia

Idempotencia acontece em duas camadas:

- `payment_webhook_events` possui unicidade por `provider + external_id` e por `provider + idempotency_key`.
- `ai_wallet_transactions` usa `idempotency_key=wallet_topup:{provider}:{idempotency_key}`.

Se o mesmo webhook chegar duas vezes, o segundo retorna `already_processed` e nao gera novo credito.

## Seguranca

- Payload completo de webhook nao e persistido.
- `payload_summary_json` guarda apenas chaves, status e external_id.
- `payment_data_json` guarda apenas campos permitidos para retorno ao cliente.
- PSP real falha fechado quando `PAYMENT_REAL_ENABLED=false`.
- Credenciais reais devem ficar apenas em `.env.local` ou secret manager, nunca no repo.

## Limitacoes

- O adapter real e um placeholder seguro.
- O stack nao guarda dados bancarios.
- O stack nao concilia chargebacks, expiracao ou estorno automatico nesta etapa.
