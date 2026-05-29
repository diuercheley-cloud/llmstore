---
owner: platform-ops
status: consolidated
---

# Advanced Visual Observability

O `llm-inference-stack` fornece uma experiência de observabilidade avançada baseada em Grafana, Prometheus e métricas nativas do Control Plane.

## Dashboards Grafana

Os dashboards estão versionados em `monitoring/dashboards/` e podem ser provisionados automaticamente em qualquer instância do Grafana.

### Dashboards Disponíveis:
- **Platform Overview**: Visão geral de disponibilidade, RPS e latência.
- **Runtime Nodes**: Status detalhado de saúde e recursos de cada nó.
- **GPU Capacity**: Métricas profundas de memória e temperatura de GPU (via nvidia-smi).
- **SLO & Error Budget**: Acompanhamento rigoroso dos compromissos de nível de serviço.

## SLO e Error Budget

O sistema utiliza o conceito de **Error Budget** para gerenciar o risco de novas releases e mudanças.
- **SLO Alvo**: 99.9% de disponibilidade.
- **Burn Rate**: Velocidade com que o orçamento de erro está sendo consumido. Se o burn rate for > 1, o orçamento está acabando mais rápido do que o esperado para o período.

## Alertas de Produção

As regras de alerta estão definidas em `monitoring/alert_rules/llm_alerts.yml`.
- **Crítico**: Alta taxa de erro (>5%), queda de nós principais.
- **Aviso**: Latência p95 degradada, pressão de memória GPU, falhas repetidas de RBAC.

> [!CAUTION]
> **Privacidade**: O sistema de observabilidade é projetado para nunca coletar ou exibir prompts, respostas de modelos ou chaves de API reais nas métricas ou logs de incidentes.
