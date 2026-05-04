# Venda de API de Inferência (LM Studio + Billing)

Este documento descreve como configurar e operar a plataforma de venda de acesso à API de inferência LLM utilizando o LM Studio como backend primário e o Control Plane existente como Gateway de Autenticação e Billing.

## Arquitetura

1. **LM Studio (Backend)**: Roda o modelo localmente (ex: `nvidia/nemotron-3-nano-4b`) e expõe um servidor OpenAI-compatible na rede local. Não requer autenticação própria e não deve ser exposto à internet.
2. **Control Plane (API Gateway)**: O sistema principal recebe chamadas em `POST /v1/chat/completions`, autentica o cliente usando uma API key segura (hash no banco), valida limites de taxa (RPM, cotas diárias/mensais), redireciona a chamada para o LM Studio e contabiliza os tokens (streaming ou non-streaming).

## Variáveis de Ambiente (.env)

Para ativar a integração com o LM Studio, configure no `.env` do seu Control Plane:

```ini
LMSTUDIO_ENABLED=true
LMSTUDIO_BASE_URL=http://192.168.101.1:1234/v1
LMSTUDIO_API_KEY=
LMSTUDIO_DEFAULT_MODEL=nvidia/nemotron-3-nano-4b
```

## Operação Administrativa

O sistema possui endpoints administrativos em `/admin/...` protegidos por `X-Admin-Token`.

### 1. Consultar Planos
Existem planos padrão (ex: `basic`). Para consultar e obter o ID do plano:
```bash
curl -H "X-Admin-Token: $ADMIN_TOKEN" http://localhost:18080/admin/billing-plans
```

### 2. Criar Cliente
Associe um plano e defina limites para o cliente:
```bash
curl -X POST -H "X-Admin-Token: $ADMIN_TOKEN" \
     -H "Content-Type: application/json" \
     http://localhost:18080/admin/clients -d '{
  "name": "Cliente Empresa A",
  "billing_status": "active",
  "billing_plan_id": "<ID_DO_PLANO>",
  "rate_limit_per_minute": 5,
  "daily_token_quota": 50000,
  "monthly_token_quota": 2000000
}'
```

### 3. Gerar API Key
O sistema retorna a chave completa apenas na criação. O banco armazena apenas um hash SHA-256 da chave.
```bash
curl -X POST -H "X-Admin-Token: $ADMIN_TOKEN" \
     -H "Content-Type: application/json" \
     http://localhost:18080/admin/api-keys -d '{
  "client_id": "<ID_DO_CLIENTE>",
  "name": "Chave de Producao"
}'
```
Copie a chave gerada (ex: `sk_...`).

### 4. Consultar Consumo
Para faturamento e acompanhamento de limite:
```bash
curl -H "X-Admin-Token: $ADMIN_TOKEN" \
     http://localhost:18080/admin/usage/<ID_DO_CLIENTE>/summary
```

## Chamada do Cliente

O cliente final nunca acessa o LM Studio diretamente. Ele usa o Control Plane:

```bash
curl http://localhost:18080/v1/chat/completions \
  -H "Authorization: Bearer sk_cliente_xxx" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nvidia/nemotron-3-nano-4b",
    "messages": [
      {
        "role": "user",
        "content": "Explique BGP em 3 frases."
      }
    ],
    "temperature": 0.2,
    "max_tokens": 200
  }'
```

## Checklist para Produção

- [ ] Bloquear portas do LM Studio no firewall para acesso externo (apenas o IP do Control Plane deve acessar).
- [ ] Alterar o `ADMIN_TOKEN` para um valor seguro.
- [ ] Configurar HTTPS via Caddy ou Nginx (já incluído no projeto).
- [ ] Monitorar uso com os logs do Docker (`docker compose logs -f control-plane`).