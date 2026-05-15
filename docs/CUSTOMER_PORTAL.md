# Customer Portal

O portal do cliente fica em `http://localhost:18080/client-portal` e usa autenticação por API key do próprio cliente.

## Áreas disponíveis

- `Minhas API Keys`
  - lista chaves mascaradas
  - cria nova chave
  - revoga chave
  - copia exemplo de uso
- `Uso`
  - requests hoje/mês
  - tokens hoje/mês
  - preço visível ao cliente quando houver dados financeiros; fallback para preview de invoice no mês
  - quota restante
  - rate limit atual
- `Faturas`
  - lista invoices do próprio cliente
  - exibe `pending`, `paid`, `overdue`, `cancelled`
  - baixa JSON ou HTML simples por invoice
- `Wallet`
  - saldo atual
  - histórico de transações
  - aviso de saldo baixo
  - `Solicitar Recarga` gera lead interno (`source=portal_wallet_recharge`) sem PSP real
  - `/portal/wallet/topups` cria/lista intenções de recarga via adapter opcional (`disabled` por padrão, `mock` para testes locais)
- `Playground`
  - usa `/v1/chat/completions`
  - seletor de modelo
  - estimativa simples de tokens
  - mensagens amigáveis para bloqueios por quota, rate limit e billing
- `Exemplos`
  - `curl`
  - `Python`
  - `Node.js`
  - `base_url` OpenAI-compatible

## Segurança

- Todas as rotas usam autenticação do cliente via `Authorization: Bearer <api_key>`.
- O portal só consulta dados filtrados por `client_id` autenticado.
- Downloads de invoice validam posse da invoice antes de responder.
- O portal não expõe `provider_api_key`, `provider_cost_brl`, `gross_profit_brl`, `margin_percent` nem prompts de outros clientes.
- A wallet do portal usa serialização sanitizada de transações, sem `idempotency_key` ou `metadata_json` interno.
- Topups PSP/PIX persistem apenas dados sanitizados; webhook guarda resumo, não payload bruto.

## Endpoints do portal

- `GET /portal/me`
- `GET /portal/api-keys`
- `POST /portal/api-keys`
- `DELETE /portal/api-keys/{api_key_id}`
- `GET /portal/usage`
- `GET /portal/usage-stats`
- `GET /portal/invoices`
- `GET /portal/invoices/{invoice_id}/download?format=json|html`
- `GET /portal/wallet`
- `POST /portal/wallet/recharge-request`
- `POST /portal/wallet/topups`
- `GET /portal/wallet/topups`
- `POST /payments/webhooks/{provider}`
- `GET /portal/examples`

## Execução local

1. Suba o stack local.
2. Crie um cliente e uma API key pelo admin.
3. Abra `http://localhost:18080/client-portal`.
4. Faça login com a API key do cliente.

## Testes relacionados

```bash
pytest tests/test_customer_portal_self_service.py \
  tests/test_wallet_topups_pix_psp.py \
  tests/test_client_api_keys.py \
  tests/test_client_portal_usage.py \
  tests/test_client_portal_wallet.py \
  tests/test_multitenant_billing_portal.py \
  tests/test_client_portal_no_internal_margin.py
```
