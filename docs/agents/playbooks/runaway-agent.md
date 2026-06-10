---
owner: platform-ops
status: consolidated
---

# Runaway Agent Playbook

## Descrição
Este playbook é acionado quando um agente entra em um loop infinito, excede o número máximo de passos ou consome recursos de forma desenfreada sem atingir um estado final.

## Sintomas
- Agente com `total_steps` muito alto.
- Consumo de tokens/custo disparando em uma única run.
- Latência de run excedendo 10 minutos sem resposta.

## Procedimento de Resposta
1. **Diagnóstico**: Execute `scripts/dev/agent-incident-diagnose.sh` para confirmar o estado da run.
2. **Mitigação Imediata**: Utilize `scripts/dev/agent-run-kill.sh` para forçar o encerramento da execução.
3. **Análise**: Verifique os logs de `model_call` e `tool_call` para identificar o ponto de loop.
4. **Resolução**: Ajuste a `max_steps` na definição do agente ou corrija o prompt/lógica de decisão.

## Ação Destrutiva
- **Kill Run**: Interrompe o processo atual. Não apaga dados históricos, mas invalida o estado em memória.
