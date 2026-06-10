---
owner: platform-ops
status: consolidated
---

# Margin Dashboard

Este documento detalha o funcionamento e a validação do Painel de Margem Executivo em Tempo Real (Margin Dashboard).

## Finalidade

O Margin Dashboard foi criado para prover aos administradores uma visão executiva, agregada e em tempo real dos custos e receitas da plataforma. Ele utiliza dados da tabela `request_financials` para calcular o lucro bruto e a margem percentual, além de detalhar custos por provedor e receitas por cliente.

## Endpoint

**GET** `/admin/financials/margin-dashboard`

Endpoint seguro, acessível apenas via token de administrador (`X-Admin-Token`).

### Campos Retornados (Schema)

A resposta é um objeto JSON que contém os seguintes campos agregados referentes ao **dia atual (UTC)**:

- `generated_at_utc`: (datetime) Momento exato de geração do snapshot usado pela tela.
- `revenue_today_brl`: (float) Receita total gerada hoje.
- `cost_today_brl`: (float) Custo total com providers hoje.
- `gross_margin_today_brl`: (float) Lucro bruto (Receita - Custo).
- `gross_margin_percent_today`: (float) Margem percentual (Lucro / Receita * 100).
- `requests_today`: (int) Total de requests realizados.
- `cache_hit_rate_today`: (float) Taxa de acerto em cache (em porcentagem).
- `estimated_cache_savings_brl`: (float) Economia estimada graças ao cache.
- `requests_by_provider`: (list) Requests e custo agregados por provedor.
- `requests_by_client`: (list) Requests e receita agregados por cliente.
- `cost_by_provider`: (list) Custo agregado por provedor ordenado.
- `revenue_by_client`: (list) Receita agregada por cliente ordenada.
- `clients_with_negative_margin`: (list) Alertas de clientes operando com prejuízo (margem < 0).
- `top_expensive_models`: (list) Os 10 modelos que mais geraram custos.
- `top_profitable_clients`: (list) Os 10 clientes mais lucrativos.
- `top_loss_clients`: (list) Os 10 clientes com maior prejuízo.

**Nota de Segurança**: Este endpoint é blindado para não retornar nenhum dado sensível. Prompts inteiros, respostas do modelo e API keys **nunca** transitam nesse payload.

## Interface do Usuário (Frontend)

Uma nova aba/tela **Painel de Margem** foi adicionada à interface administrativa (`/static/admin/index.html`).
Ela apresenta cards superiores com os totais consolidados e o alerta de margem negativa, seguidos por tabelas detalhadas de `Custo por Provider`, `Modelos Mais Caros` e `Receita por Cliente`.

### Comportamento em tempo real

- A tela faz refresh automático a cada 15 segundos quando a aba `Painel de Margem` está ativa.
- O backend retorna um snapshot pontual (`generated_at_utc`) para que o operador veja quando os números foram recalculados.
- O fluxo continua 100% local/offline quando não há providers cloud habilitados; o painel lê apenas dados persistidos em `request_financials`.

## Como Validar

Para atestar o correto funcionamento da funcionalidade, basta executar o script de validação E2E desenvolvido:

```bash
./scripts/validators/validate-margin-dashboard.sh
```

Ou pelo atalho do operador:

```bash
make validate-margin-dashboard
```

O que o script testa:
1. Comunicação bem sucedida com a API via token admin.
2. Presença de todos os atributos globais de performance no JSON de resposta.
3. Ausência estrita de chaves vazadas ou trechos de conversas (prompts/completions).

Para desenvolvimento guiado por testes, os testes de integração estão em `tests/test_margin_dashboard_admin_api.py`, e podem ser validados com:
```bash
./venv/bin/pytest -q tests/test_margin_dashboard_admin_api.py
```
