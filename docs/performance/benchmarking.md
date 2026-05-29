---
owner: platform-ops
status: consolidated
---

# Benchmarking Guide

O benchmarking no llm-inference-stack pode ser feito via UI ou CLI.

## Via CLI
Use o script `scripts/benchmark-runtime.sh`:
```bash
./scripts/benchmark-runtime.sh <model_id>
```

## Métricas Detalhadas
- **TPS**: Tokens gerados por segundo.
- **Latency p99**: O pior cenário de tempo de resposta.
- **Queue Wait**: Tempo que a requisição ficou parada antes do processamento.
- **Cache Hit**: Eficácia do cache de respostas.
