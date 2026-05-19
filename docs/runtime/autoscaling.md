# Autoscaling de Runtimes

O Autoscaling permite que a plataforma ajuste automaticamente o número de instâncias de modelos com base na demanda.

## Políticas de Autoscaling

As políticas podem ser configuradas individualmente por modelo:

- `queue_depth`: Escala com base no tamanho da fila de requisições pendentes.
- `latency_p95`: Escala se a latência p95 ultrapassar um limite definido.
- `gpu_pressure`: Escala se a memória GPU do nó estiver quase cheia.

## Modos de Operação

1. **Recommendation (Padrão)**: O autoscaler apenas sugere mudanças e registra eventos, sem executar ações destrutivas.
2. **Active**: O autoscaler executa o provisionamento e desprovisionamento automático de instâncias (requer Kubernetes ou Proxmox configurado).

## Cooldown

Para evitar o efeito de "flapping" (escalar subir e descer rapidamente), existe um período de cooldown configurável (padrão 300 segundos) entre as ações.
