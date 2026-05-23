# Queue Saturation Playbook

## Descrição
A saturação da fila ocorre quando o volume de novas runs excede a capacidade de processamento dos workers, levando a latências altas e possíveis quedas por OOM ou exaustão de conexões.

## Sintomas
- `llm_agent_jobs_queued` crescendo exponencialmente.
- Workers operando em 100% de CPU/Memória.
- Latência de início de run (`queue_wait_seconds`) degradada.

## Procedimento de Resposta
1. **Contenção**: Ative o throttle na fila usando `scripts/agent-queue-throttle.sh`.
2. **Escalonamento**: Aumente o número de réplicas de workers agentic.
3. **Priorização**: Priorize runs de classes críticas (`security`, `billing`) em detrimento de `rag_research`.
4. **Limpeza**: Cancele runs de baixa prioridade que estão na fila há muito tempo.

## Ação Destrutiva
- **Queue Throttle**: Limita a entrada de novas tarefas. Pode resultar em erros 429 para os clientes.
pired` e falha as runs associadas.
