# Unified Agentic API (v1)

A API v1 (`/v1/agents`) é a superfície canônica para integração de fluxos agentic no `llm-inference-stack`. Ela unifica o runtime de execução sob um contrato único, garantindo isolamento de tenant e aplicação rigorosa de políticas.

## Endpoints Canônicos

### Gerenciamento de Agentes
- `GET /v1/agents`: Lista definições de agentes do tenant.
- `POST /v1/agents`: Cria uma nova definição de agente.
- `GET /v1/agents/{agent_id}`: Detalhes de um agente específico.

### Execução de Runs
- `POST /v1/agents/{agent_id}/runs`: Inicia uma nova execução (Run).
- `GET /v1/agents/runs/{run_id}`: Consulta status e resumo de uma Run.
- `POST /v1/agents/runs/{run_id}/cancel`: Interrompe uma execução ativa.
- `GET /v1/agents/runs/{run_id}/events`: Stream SSE de eventos da execução.

## Compatibilidade Retrospectiva (/agents)

O endpoint `/agents` é considerado **legado** e destinado apenas para compatibilidade temporária e operações administrativas rápidas.

- Todas as chamadas para `/agents` retornam os headers:
  - `X-Deprecated-Endpoint: true`
  - `X-Replacement-Endpoint: /v1/agents`
- O runtime utilizado por `/agents` é o mesmo da `/v1/agents`, garantindo consistência de estado.

## Fluxo de Execução Canônico

Toda execução iniciada pela API gera obrigatoriamente:
1. **AgentRun**: Registro mestre da execução.
2. **AgentRunStep**: Passos granulares (model calls, tool calls).
3. **AgentRunEvent**: Eventos de observabilidade para streaming.

## Segurança e Isolamento

- **Multi-tenancy**: O isolamento de tenant é obrigatório. Uma requisição v1 só pode acessar recursos vinculados ao seu `client_id`.
- **Policy Engine**: Todas as ativações de run passam pelo `AgentPolicyEngine` para validação de quotas e permissões.
