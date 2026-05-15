# Prepaid Wallet BRL

## Visão Geral

Sistema de carteira digital pré-paga em BRL para consumo de IA.
Cliente faz recarga, ganha créditos e utiliza a API.
O ledger continua local; PSP/PIX real é opcional e fica desabilitado por padrão.

## Tabelas

### ai_wallets

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | UUID PK | Identificador único |
| client_id | UUID FK | Cliente (1:1) |
| currency | string | "BRL" |
| balance_brl | numeric(14,4) | Saldo disponível |
| reserved_brl | numeric(14,4) | Saldo reservado |
| status | string | active, frozen, closed |
| created_at | timestamp | |
| updated_at | timestamp | |

### ai_wallet_transactions

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | UUID PK | |
| wallet_id | UUID FK | Carteira |
| client_id | UUID FK | Cliente |
| type | string | manual_credit, usage_debit, refund, adjustment, reservation, release, future_pix_credit |
| amount_brl | numeric(14,4) | Valor da transação |
| balance_after_brl | numeric(14,4) | Saldo após transação |
| reference_type | string? | request_log, invoice, etc. |
| reference_id | string? | ID de referência |
| idempotency_key | string? | Chave de idempotência (unique) |
| metadata_json | text? | Metadados adicionais |
| created_by | string | admin, system, client |
| created_at | timestamp | |

## Regras de Negócio

- **Saldo negativo não permitido** (exceto se plano permitir crédito)
- **Ledger append-only**: transações nunca são alteradas ou deletadas
- **Idempotência**: credit_manual e adjustment suportam idempotency_key
- **Admin token obrigatório** para operações administrativas
- **Cliente vê apenas saldo e transações** — não pode creditar manualmente
- **PSP/PIX real opt-in**: desabilitado por padrão; mock disponível para testes locais

## Fluxo de Crédito Manual

```
Admin → POST /admin/billing/wallets/{client_id}/manual-credit
         → wallet_service.credit_manual()
         → AiWallet.balance_brl += amount
         → AiWalletTransaction (type=manual_credit, append-only)
```

## Fluxo de Débito por Uso

```
Request → wallet_service.debit_usage()
          → verifica saldo suficiente (balance - reserved >= amount)
          → AiWallet.balance_brl -= amount
          → AiWalletTransaction (type=usage_debit, append-only)
          → Se saldo insuficiente: InsufficientBalance → bloqueia cloud
```

## Endpoints Admin

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | /admin/billing/wallets | Listar todas carteiras |
| GET | /admin/billing/wallets/{client_id} | Obter carteira |
| POST | /admin/billing/wallets/{client_id}/manual-credit | Creditar manualmente |
| POST | /admin/billing/wallets/{client_id}/adjustment | Ajustar saldo |
| GET | /admin/billing/wallets/{client_id}/transactions | Listar transações |

Protegidos por `X-Admin-Token`.

## Client Portal

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | /portal/wallet | Saldo, transações, aviso PIX |
| POST | /portal/wallet/topups | Criar intenção de recarga via adapter configurado |
| GET | /portal/wallet/topups | Listar recargas do próprio cliente |

## Serviço

`control_plane/app/services/billing/wallet_service.py`

| Função | Descrição |
|--------|-----------|
| get_or_create_wallet() | Obtém ou cria carteira |
| credit_manual() | Crédito manual (admin) |
| debit_usage() | Débito por uso |
| reserve_amount() | Reserva valor |
| release_reservation() | Libera reserva |
| refund() | Estorno |
| adjustment() | Ajuste manual |
| get_balance() | Saldo atual |
| ensure_idempotency() | Verifica idempotência |
| list_transactions() | Lista transações |

## Segurança

- PSP/PIX real fica bloqueado salvo `PAYMENT_REAL_ENABLED=true`
- Nenhum dado bancário armazenado
- Admin token validado em todas as operações administrativas
- Cliente não pode modificar saldo

Detalhes do fluxo de topups, webhook e idempotência: `docs/WALLET_TOPUPS_PIX_PSP.md`.

## Real Billing Margin Validation
Prepaid wallets are debited accurately during real requests validation.
