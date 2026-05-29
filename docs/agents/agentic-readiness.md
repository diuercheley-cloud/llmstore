---
owner: platform-ops
status: consolidated
---

# Agentic Runtime Readiness

O Agentic Runtime Readiness é uma ferramenta de diagnóstico "honesta" projetada para refletir o estado real e operacional do runtime de agentes no `llm-inference-stack`. Seu objetivo é eliminar falsos positivos e fornecer uma visão clara de bloqueios, degradações e necessidades de manutenção.

## Status Operacionais

- **`ready`**: O runtime está habilitado, workers estão ativos e não há incidentes críticos bloqueando a execução.
- **`disabled`**: O runtime de agentes está desativado via configuração (`AGENT_RUNTIME_ENABLED=false`).
- **`degraded`**: O runtime está operacional, mas existem problemas não bloqueantes, como execuções presas (stuck runs), itens na DLQ ou backlog de aprovações.
- **`blocked`**: O runtime está habilitado, mas não pode operar corretamente (ex: nenhum worker ativo quando `AGENT_WORKER_ENABLED=true`).
- **`unknown`**: Não foi possível determinar o estado devido a falhas internas no próprio check.

## Principais Verificações

1.  **Runtime Habilitado**: Verifica `AGENT_RUNTIME_ENABLED`.
2.  **Heartbeat de Workers**: Garante que existem workers comunicando-se com o Control Plane nos últimos 2 minutos.
3.  **Execuções Presas**: Detecta runs em estado `running` por mais de 1 hora.
4.  **Dead Letter Queue (DLQ)**: Alerta sobre falhas definitivas no processamento de jobs.
5.  **Backlog de Aprovações/Incidentes**: Monitora a carga de trabalho humana e operacional pendente.
6.  **Políticas de Memória**: Verifica se existem políticas configuradas para os tenants.

## Como Executar

### CLI (Makefile)
```bash
make agentic-readiness
```

### API Administrativa
- **GET** `/admin/agents/readiness`: Retorna o status atual e os checks detalhados.
- **POST** `/admin/agents/readiness/run`: Força uma nova execução completa do diagnóstico.

## Estrutura da Resposta

Toda resposta de readiness contém:
- `status`: O estado consolidado.
- `checks[]`: Lista detalhada de cada verificação individual.
- `blockers[]`: Mensagens de erro que impedem o funcionamento.
- `warnings[]`: Alertas sobre saúde degradada.
- `recommendations[]`: Sugestões de ação para normalizar o sistema.
