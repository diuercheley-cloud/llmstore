---
owner: platform-ops
status: consolidated
---

# Commercial Revenue Protection

`Commercial Revenue Protection` converte anomalias financeiras em ações comerciais seguras e reversíveis.

## Policies

Cada `CommercialRevenueProtectionPolicy` define:

- `trigger_type`: `cost_spike`, `margin_drop`, `wallet_debit_spike`, `qos_billing_spike`, `revenue_drop`, `dispute_spike`
- `severity_threshold`: `low`, `medium`, `high`, `critical`
- `action_type`: `notify`, `safe_mode`, `restrict_expensive_models`, `force_local_only`, `reduce_qos_priority`, `require_manual_approval`
- `scope_type`: `global`, `client`, `provider`, `model`, `qos_tier`
- `mode`: `report_only`, `approval_required`, `enforce`
- `cooldown_minutes`: evita repeticao excessiva

## Triggers

O engine usa `CommercialFinancialAnomaly` como fonte principal de triggers nesta fase.

- `cost_spike`: aumento anormal de custo
- `margin_drop`: queda anormal de margem
- `wallet_debit_spike`: pico de debito em wallet opt-in
- `qos_billing_spike`: pico de cobranca QoS
- `revenue_drop`: queda anormal de receita
- `dispute_spike`: aumento anormal de disputas

## Actions

- `notify`: gera alerta interno e pode fazer webhook sanitizado
- `safe_mode`: ativa modo conservador por cliente, tipicamente `force_local_only` e risco reduzido
- `restrict_expensive_models`: restringe modelos com custo alto ou margem negativa
- `force_local_only`: remove rotas cloud para o escopo afetado
- `reduce_qos_priority`: reduz prioridade efetiva do tier/cliente
- `require_manual_approval`: marca futuras decisoes caras como dependentes de aprovacao

## Modes

- `disabled`: desliga o mecanismo
- `report_only`: apenas cria `proposed`
- `approval_required`: cria `pending_approval`
- `enforce`: tenta aplicar apenas acoes nao destrutivas e somente se `COMMERCIAL_REVENUE_PROTECTION_ALLOW_ENFORCE=true`

## Cooldown

Cada policy tem `cooldown_minutes`. Durante a janela ativa, novas ocorrencias equivalentes viram `skipped`.

## Safe Mode

`safe_mode` nao bloqueia clientes globalmente. Nesta fase ele:

- prioriza local-first
- pode forcar `force_local_only`
- pode reduzir `max_cost_override`

## Routing Constraints

`get_active_revenue_protection_constraints(client_id, provider, model, qos_tier)` retorna:

- `force_local_only`
- `restricted_models`
- `max_cost_override`
- `qos_priority_override`
- `require_approval`

Essas constraints alimentam:

- commercial guardrails
- commercial routing
- QoS routing
- model policy

## Webhook

Servico: `control_plane/app/services/notifications/revenue_alerts.py`

- sempre sanitiza payload
- `COMMERCIAL_REVENUE_PROTECTION_WEBHOOK_ENABLED=false`: log interno apenas
- `enabled=true` sem URL: dry-run
- `enabled=true` com URL: webhook real generico

## Riscos

- o cache de constraints e em processo; apos restart ele depende de rebuild em runtime
- esta fase nao altera billing automaticamente
- esta fase nao resolve disputas automaticamente
- esta fase nao envia Slack/PagerDuty/Email nativos ainda
- acoes destrutivas continuam bloqueadas por padrao
