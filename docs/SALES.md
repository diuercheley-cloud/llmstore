# SaaS Sales Flow

## Objetivo

Transformar o stack em um produto vendavel com onboarding self-serve, plano free limitado, pagina publica de oferta e deploy simples em VPS.

### Technical Readiness & Safety
O sistema inclui ferramentas de auto-diagnóstico para garantir o sucesso da venda:

- **Pre-Demo Checklist**: `make pre-demo-check` (Garante que a demo não falhe ao vivo).
- **Pre-Client Checklist**: `make pre-client-check` (Valida segurança e performance antes da entrega).
- **Security Report**: Relatório detalhado de mitigação de riscos.

## Fluxo comercial

1. O visitante acessa `/` para entender a proposta do produto.
2. O visitante compara planos em `/pricing`.
3. O cadastro acontece em `/signup` ou direto no endpoint `POST /public/signup`.
4. O control plane cria o cliente, associa o plano e gera uma API key inicial.
5. O cliente usa a chave em `/v1/*` e acompanha uso, invoices e teste de prompt em `/client-portal`.

## Onboarding automatico

O endpoint `POST /public/signup` retorna:

- `client_id`
- `account_name`
- `plan_code`
- `api_key`
- `portal_url`
- `api_base_url`

A API key e retornada apenas uma vez. O cliente deve armazenar esse valor no momento do cadastro.

## Oferta comercial padrao (Local Edition)

O sistema utiliza faturamento local/manual nesta versão.

| Recurso | Free | Basic | Pro | Enterprise Local |
| :--- | :--- | :--- | :--- | :--- |
| **Requisições (RPM/RPD)** | 10 / 100 | 30 / 1.000 | 60 / 5.000 | 300 / 1.000.000 |
| **Tokens (Mês)** | 50.000 | 500.000 | 5.000.000 | 50.000.000 |
| **Contexto Máximo** | 4.096 | 8.192 | 16.384 | 131.072 |
| **Streaming** | Sim | Sim | Sim | Sim |
| **RAG** | Não | Sim (5 docs) | Sim (50 docs) | Sim (1.000 docs) |
| **TTS** | Não | Sim | Sim | Sim |
| **Embeddings** | Não | Sim | Sim | Sim |
| **Exportação de Uso** | Não | Não | Sim | Sim |
| **Suporte** | Comunitário | E-mail | E-mail Prioritário | 24/7 Dedicado |

**Nota:** O faturamento é realizado de forma manual/local. Não há integração direta com PSP/PIX nesta versão.

## Deploy publico

Em producao, use `STACK_MODE=prod` e `scripts/deploy-vps.sh`. O compose de producao sobe o Caddy na frente do control plane para obter HTTPS automatico com Let's Encrypt.

## Operacao de venda

- Use a landing como CTA principal.
- Direcione campanhas para `/pricing`.
- Entregue trial ou free via `/signup`.
- Faça upgrade de plano pelo Admin API ou pelo fluxo comercial interno.
