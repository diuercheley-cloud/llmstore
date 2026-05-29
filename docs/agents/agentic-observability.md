---
owner: platform-ops
status: consolidated
---

# Agentic Observability

Este documento descreve as métricas e dashboards nativos para monitoramento de agentes no LLM Inference Stack.

## Métricas Disponíveis

As seguintes métricas são exportadas via Prometheus:

| Métrica | Tipo | Descrição |
|---------|------|-----------|
| `llm_agent_run_success_rate` | Gauge | Taxa de sucesso das execuções (1.0 = sucesso, 0.0 = falha). |
| `llm_agent_plan_depth` | Gauge | Profundidade atual do plano do agente. |
| `llm_agent_tool_latency_seconds` | Histogram | Latência de execução de ferramentas. |
| `llm_agent_tool_failure_rate` | Gauge | Taxa de falha de chamadas de ferramentas. |
| `llm_agent_approval_wait_seconds` | Histogram | Tempo de espera por aprovação humana. |
| `llm_agent_token_budget_used` | Gauge | Tokens consumidos em relação ao orçamento. |
| `llm_agent_cost_budget_used_brl` | Gauge | Custo em BRL em relação ao orçamento. |
| `llm_agent_memory_hit_rate` | Gauge | Taxa de acerto (hit rate) da memória do agente. |
| `llm_agent_replan_total` | Counter | Total de replanejamentos executados. |
| `llm_agent_handoff_depth` | Gauge | Profundidade de handoffs entre agentes. |
| `llm_agent_policy_denials_total` | Counter | Total de negações por política de segurança. |

## Dashboards Grafana

Os seguintes dashboards estão disponíveis em `monitoring/dashboards/`:

1.  **Agentic Overview**: Visão geral de saúde, volume de execuções e profundidade de planos.
2.  **Agentic Tools**: Performance e confiabilidade das ferramentas (tools).
3.  **Agentic Memory**: Latência e hit rate de memória (curto e longo prazo).
4.  **Agentic Approvals**: Backlog de aprovações e eficácia das guardrails.
5.  **Agentic Costs**: Consumo de tokens e custos estimados em BRL.

## Admin UI: Agentic Operations Dashboard

O dashboard de operações na interface administrativa oferece uma visão consolidada para o operador:

-   **Platform Health**: Status dos sistemas de observabilidade e guardrails.
-   **Tool Latency & Memory Hit Rate**: Indicadores de performance técnica.
-   **Approval Backlog**: Fila de ações que requerem intervenção humana.
-   **Budget Usage**: Monitoramento de limites financeiros e de tokens.
-   **Incident Timeline**: Histórico de eventos críticos e falhas automatizadas.

## Configuração

Para habilitar a observabilidade detalhada, garanta que as seguintes flags estejam ativas no seu `.env` ou `config.yaml`:

```yaml
agent_observability_enabled: true
agent_trace_export_enabled: true
```

## Segurança

O sistema de observabilidade sanitiza automaticamente payloads, removendo strings que contenham padrões de segredos (`SECRET_`, `KEY_`, `TOKEN_`) e campos de `prompt` para evitar vazamento de dados sensíveis em logs e eventos de timeline.

## Operational Guide (Production Ready)

### Activate
Ensure `AGENT_OBSERVABILITY_ENABLED=true`.

### Monitor
Standard Prometheus/Grafana stack.

### Troubleshoot
Check observability service logs.

### Rollback
Disable the observability flag.
