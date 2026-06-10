---
owner: platform-ops
status: consolidated
---

# Tool Cascade Failure Playbook

## Descrição
Ocorre quando uma ferramenta externa ou serviço dependente começa a falhar sistematicamente, causando falhas em cadeia em múltiplos agentes.

## Sintomas
- Aumento súbito na métrica `llm_agent_tool_failure_rate`.
- Logs de erro 5xx em chamadas de ferramentas específicas.
- Múltiplos agentes travados no mesmo passo de execução.

## Procedimento de Resposta
1. **Identificação**: Identifique a ferramenta problemática via dashboard "Agentic Tools".
2. **Mitigação**: Execute `scripts/dev/agent-disable-tool.sh` para desabilitar a ferramenta globalmente ou para o agente específico.
3. **Comunicação**: Notifique os donos dos agentes sobre a indisponibilidade da ferramenta.
4. **Recuperação**: Após a normalização do serviço externo, habilite a ferramenta novamente.

## Ação Destrutiva
- **Disable Tool**: Impede que qualquer agente utilize a ferramenta. Pode causar falhas de planejamento se o agente não tiver alternativas.
