---
owner: platform-ops
status: consolidated
---

# Runtime Canonical API Architecture

O `llm-inference-stack` utiliza uma arquitetura de runtime unificada para garantir que todos os agentes, independentemente da porta de entrada da API, sigam o mesmo ciclo de vida e regras de governança.

## AgentApiFacade

A `AgentApiFacade` (`app.services.agents.agent_api_facade`) atua como o ponto de entrada único para todas as operações de runtime. Suas responsabilidades incluem:

- **Validação de Identidade**: Garantir que o solicitante tem acesso ao agente/run.
- **Checagem de Políticas**: Invocar o `AgentPolicyEngine` antes de qualquer execução.
- **Orquestração de Runtime**: Chamar o `AgentRuntime` para manipulação de estado (start, pause, resume, cancel).
- **Sanitização**: Filtrar dados sensíveis de payloads antes de serem expostos via API.

## Arquitetura de Execução

```
[ API /v1/agents ] ----\
                        --> [ AgentApiFacade ] --> [ AgentRuntime ] --> [ AgentExecutor ]
[ API /agents    ] ----/
```

### Unificação de Estado

Não existe caminho divergente para execução. Tanto a API pública quanto a administrativa utilizam o `AgentRuntime.start_run`, o que garante que:
- Logs de auditoria sejam idênticos.
- O rastreio de custos e tokens seja centralizado.
- O streaming de eventos (`/events`) funcione consistentemente para qualquer run.

## Regras de Transição de Estado

O runtime garante a integridade das transições de estado:
- `queued` -> `running` (via Worker ou Sync Loop)
- `running` -> `completed` | `failed` | `cancelled`
- `running` -> `paused` (via `/pause`)
- `paused` -> `running` (via `/resume`)

## Operational Guide (Production Ready)

### Activate
Ensure `AGENT_RUNTIME_ENABLED=true` in your environment configuration.

### Monitor
Monitor metrics via `/admin/agents/observability/metrics`. Look for `agent_execution_latency` and `agent_error_rate`.

### Troubleshoot
Check logs for `agent-runtime` prefix. Use `/admin/readiness/agent-runtime` to check sub-service health.

### Rollback
Set `AGENT_RUNTIME_ENABLED=false` to fallback to legacy execution or revert deployment to previous stable tag.
