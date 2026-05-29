---
owner: platform-ops
status: consolidated
---

# Agentic Runtime Contracts

O `llm-inference-stack` utiliza contratos versionados para garantir a estabilidade e previsibilidade das interações entre os componentes do runtime agentic (planner, executor, ferramentas e memória).

## Princípios dos Contratos

- **Versionamento Semântico**: Cada contrato possui uma versão maior (v1, v2) que reflete mudanças quebras de compatibilidade.
- **Validação de Entrada/Saída**: Todos os dados que cruzam as fronteiras dos componentes são validados contra schemas Pydantic.
- **Políticas de Compatibilidade**: Por padrão, os contratos seguem uma política de compatibilidade retroativa (`backward`), permitindo a adição de campos sem quebrar implementações antigas.

## Contratos Formalizados

### 1. Runtime Contract (`AgentRunRequestV1`, `AgentRunResultV1`)
Define como uma requisição de execução de agente deve ser formatada e o que o runtime retorna após a conclusão (ou falha).

### 2. Planner Contract (`AgentPlanV1`, `AgentTaskV1`)
Define a estrutura de um plano gerado pelo agente, incluindo a lista de tarefas e dependências. Garante que o Executor saiba exatamente como processar cada passo.

### 3. Tool Call Contract (`AgentToolCallV1`, `AgentToolResultV1`)
Formaliza a interface de invocação de ferramentas, padronizando como os parâmetros são passados e como os resultados (sucesso/erro) são reportados.

### 4. Memory Injection Contract (`AgentMemoryContextV1`, `AgentMemoryCitationV1`)
Define como o contexto de memória (RAG) é injetado no prompt do agente, incluindo citações estruturadas para auditabilidade.

## Exemplo de Uso

```python
from app.contracts.agents.runtime_contract import RuntimeContractV1

# Validando entrada
request_data = {...}
validated_request = RuntimeContractV1.validate_input(request_data)

# Validando saída do componente
result_data = {...}
validated_result = RuntimeContractV1.validate_output(result_data)
```
