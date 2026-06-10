---
owner: platform-ops
status: consolidated
---

# Agent Worker Operations

O `agent-worker` é o componente responsável pela execução assíncrona de agentes no `llm-inference-stack`. Ele processa tarefas da fila, gerencia leases de execução e reporta saúde periodicamente.

## Implantação

### Docker Compose
Para iniciar o worker com o profile `agentic`:
```bash
docker-compose --profile agentic up -d agent-worker
```

### Kubernetes
O worker é implantado como um Deployment com suporte a HPA:
```bash
kubectl apply -f deploy/kubernetes/agent-worker.yaml
```

## Operações Comuns

### Verificar Status
Para visualizar a saúde global dos workers e da fila:
```bash
make agentic-readiness
# ou
./scripts/dev/agent-worker-status.sh
```

### Graceful Shutdown (Drain)
Para remover um worker de operação sem interromper a tarefa atual (ex: antes de um restart ou escala negativa):
```bash
./scripts/dev/agent-worker-drain.sh <worker_id_ou_pod_name>
```
O worker enviará um sinal `SIGUSR1` para si mesmo, entrará em modo `draining`, concluirá o job ativo e parará de buscar novos.

## Auto-scaling
O worker escala horizontalmente baseado no consumo de CPU e profundidade da fila (via HPA no Kubernetes). Recomenda-se manter um mínimo de 2 réplicas para alta disponibilidade.

## Métricas de Operação (Prometheus)
- `llm_agent_active_workers`: Número de workers enviando heartbeat.
- `llm_agent_jobs_queued`: Profundidade da fila por tenant/agente.
- `llm_agent_dead_letters_total`: Total de falhas definitivas.
- `llm_agent_drain_status`: Indica se um worker está em modo de esvaziamento.
