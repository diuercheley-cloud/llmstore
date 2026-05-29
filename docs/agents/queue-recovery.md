---
owner: platform-ops
status: consolidated
---

# Agent Queue Recovery

O runtime agentic utiliza um sistema de fila persistente com mecanismos de recuperação automática para lidar com falhas de infraestrutura, crashes de workers e instabilidades de rede.

## Mecanismos de Recuperação

### 1. Orphan Lease Recovery
Quando um worker trava abruptamente, o job que ele estava processando fica com uma "lease" órfã. 
- O sistema de recuperação identifica leases expiradas (sem renovação por > 60s).
- O job é automaticamente retornado ao estado `queued`.
- O histórico de tentativas é preservado.

### 2. Dead Letter Queue (DLQ)
Jobs que falham repetidamente (padrão: 3 tentativas com backoff exponencial) são movidos para a DLQ.
- O status da run é marcado como `failed`.
- O erro final é registrado no evento `dead_letter`.

### 3. Stuck Run Detection
Runs que permanecem no status `running` por mais de 2 horas sem nenhuma atualização de passo são sinalizadas como `stuck`. O sistema de monitoramento eleva métricas de alerta para intervenção manual.

## Intervenção Manual

### Inspecionar DLQ
```bash
./scripts/agent-dlq-inspect.sh
```

### Reprocessar Job da DLQ
Caso a falha tenha sido causada por um problema temporário de infraestrutura já resolvido:
```bash
./scripts/agent-dlq-retry.sh <dlq_item_id>
```
Isso resetará o contador de tentativas e colocará o job de volta na fila principal.

### Teste de Recuperação
Para validar se o seu ambiente está recuperando jobs corretamente:
```bash
./scripts/agent-queue-recovery-test.sh
```
Siga as instruções do script para simular falhas controladas.
