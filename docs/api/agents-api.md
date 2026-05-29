---
owner: platform-ops
status: consolidated
---

# Agents Public API (v1)

A API v1 permite que aplicações externas integrem fluxos agentic da plataforma de forma segura e multi-tenant.

## Autenticação

Todas as chamadas exigem um `Authorization: Bearer <API_KEY>` no cabeçalho. As chaves de API são vinculadas a um inquilino (tenant) específico e garantem o isolamento dos dados.

## Endpoints de Agentes

### Listar Agentes
`GET /v1/agents`
Retorna todos os agentes disponíveis para o inquilino.

### Obter Agente
`GET /v1/agents/{agent_id}`
Retorna detalhes de um agente específico.

### Criar Agente
`POST /v1/agents`
Permite definir um novo agente programaticamente.

## Execuções (Runs)

### Iniciar Execução
`POST /v1/agents/{agent_id}/runs`
**Body**:
```json
{
  "input_text": "Sua solicitação para o agente"
}
```

### Consultar Status
`GET /v1/agents/runs/{run_id}`
Retorna o estado atual da execução (`queued`, `running`, `completed`, `failed`, `cancelled`).

### Cancelar Execução
`POST /v1/agents/runs/{run_id}/cancel`

## Streaming de Eventos (SSE)

### Assinar Eventos
`GET /v1/agents/runs/{run_id}/events`
Abre uma conexão Server-Sent Events para monitorar o progresso em tempo real.

**Eventos Emitidos**:
- `run.started`: A execução foi aceita e iniciada.
- `step.completed`: Um passo interno (ex: chamada de modelo) foi concluído.
- `tool.called`: Uma ferramenta externa foi invocada.
- `run.completed`: O agente atingiu seu objetivo final.
- `run.failed`: A execução foi interrompida por erro ou política.

## Governança e Limites

- **Isolamento**: Um inquilino nunca pode acessar ou executar agentes de outro inquilino.
- **Políticas**: Todas as execuções via API pública passam pelo `AgentPolicyEngine`, respeitando limites de passos, custos e restrições de ferramentas.
- **Sanitização**: Eventos de streaming não contêm prompts brutos por padrão para proteger a propriedade intelectual das instruções do agente.
