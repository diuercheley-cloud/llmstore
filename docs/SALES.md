# SaaS Sales Flow

## Objetivo

Transformar o stack em um produto vendavel com onboarding self-serve, plano free limitado, pagina publica de oferta e deploy simples em VPS.

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

## Oferta comercial padrao

- `free`: plano gratuito com quotas pequenas, sem streaming e sem overage.
- `basic`: entrada paga para workloads compartilhados.
- `pro`: plano destacado para uso recorrente em producao.
- `enterprise`: trilha de rollout com maior capacidade e suporte prioritario.

## Deploy publico

Em producao, use `STACK_MODE=prod` e `scripts/deploy-vps.sh`. O compose de producao sobe o Caddy na frente do control plane para obter HTTPS automatico com Let's Encrypt.

## Operacao de venda

- Use a landing como CTA principal.
- Direcione campanhas para `/pricing`.
- Entregue trial ou free via `/signup`.
- Faça upgrade de plano pelo Admin API ou pelo fluxo comercial interno.
