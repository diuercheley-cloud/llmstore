# Task Engine

O Task Engine é o orquestrador responsável por executar as tarefas definidas em um plano, gerenciando estados, retentativas e concorrência.

## Estados da Tarefa

- `pending`: Aguardando execução ou dependências.
- `running`: Atualmente sendo processada.
- `blocked`: Dependências falharam ou pausadas.
- `completed`: Executada com sucesso.
- `failed`: Falha definitiva após exaustão de retentativas.
- `skipped`: Pulada manualmente por um operador.

## Retentativas Automáticas

Se `AGENT_AUTO_RETRY_ENABLED` estiver ativo, o engine tentará reexecutar tarefas que falharam por erros transientes, respeitando o `max_attempts` de cada tarefa.

## Idempotência

O Task Engine encoraja o uso de ferramentas idempotentes. Antes de cada tarefa com efeitos colaterais, o engine realiza um checkpoint do estado do agente.
