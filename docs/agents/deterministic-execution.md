---
owner: platform-ops
status: consolidated
---

# Deterministic Agent Execution

O `llm-inference-stack` garante que toda execução de agentes seja determinística, auditável e livre de efeitos colaterais em modos de simulação (replay).

## Princípios de Endurecimento

### 1. Auditoria Ponta a Ponta
Cada passo da execução produz obrigatoriamente:
- **Eventos de Timeline**: Registros granulares de início e fim de passos, chamadas de modelo e ferramentas.
- **Hashes de Dados**: O `input_hash` e `output_hash` são calculados para cada interação, permitindo validar a integridade dos dados.
- **Recibos de Execução**: Cada ferramenta executada gera um `AgentRunReceipt` assinado.

### 2. Ciclo de Vida do Executor
O `AgentExecutor` gerencia transições de estado rigorosas:
- **run_started**: Disparado assim que a execução sai da fila.
- **step_started**: Marca o início de uma unidade lógica de trabalho.
- **model_call_started/completed/failed**: Rastreia a interação com o provedor de LLM.
- **tool_call_started/completed/failed**: Rastreia a execução de ferramentas externas.
- **run_completed/failed/cancelled**: Estados terminais com justificativa explícita (`failure_reason`).

### 3. Replay Seguro
O modo `is_replay=True` permite re-processar uma execução para análise sem disparar:
- Chamadas reais a ferramentas.
- Escritas em memória.
- Novas cobranças ou consumo de tokens reais.

## Ordem Determinística
A sequência de passos é garantida por uma ordem monotônica, assegurando que o rastro de eventos reflita fielmente a cronologia da execução, facilitando a depuração e compliance.
