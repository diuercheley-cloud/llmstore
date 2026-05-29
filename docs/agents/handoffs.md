---
owner: platform-ops
status: consolidated
---

# Agent Handoffs

Handoffs permitem a delegação de autoridade de execução entre agentes especializados.

## Configuração de Políticas

As políticas de handoff (`AgentHandoffPolicy`) definem:

- **Origem e Destino**: Quais pares de agentes podem colaborar.
- **Campos de Contexto**: Quais dados (chaves do dicionário de contexto) podem ser passados para o próximo agente.
- **Máximo de Saltos**: Quantas vezes uma tarefa pode ser re-delegada.
- **Aprovação**: Se a delegação requer confirmação humana (HITL).

## Auditoria de Handoff

Cada evento de delegação é registrado como um `AgentHandoffEvent`, contendo:

- ID da corrida de origem e destino.
- Motivo alegado pelo agente para a delegação.
- Timestamp do evento.
- Chaves de contexto que foram compartilhadas.

## Segurança

- **Contexto Sanitizado**: O agente de destino não recebe o histórico completo ou o prompt original do agente de origem, apenas as chaves explicitamente permitidas pela política. Isso evita vazamento de instruções internas ou dados sensíveis não necessários.
- **Tenant Boundary**: O `tenant_id` é preservado, garantindo que o agente delegado opere nos mesmos limites de dados que o original.
