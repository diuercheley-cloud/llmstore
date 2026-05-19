# Service Level Objectives (SLOs)

Este documento define os SLOs de plataforma para o `llm-inference-stack`.

## Definições

### API Availability
- **Descrição**: Percentual de requisições que retornam status code de sucesso (não-5xx).
- **SLO**: 99.9%
- **Métrica**: `llm_requests_total` e `llm_request_errors_total`.

### Latency (p95)
- **Descrição**: Tempo de resposta de ponta a ponta para 95% das requisições.
- **SLO**: < 2.0s (pode variar por modelo)
- **Métrica**: `llm_request_latency_seconds`.

### Queue Wait Time (p95)
- **Descrição**: Tempo que uma requisição passa na fila antes de ser processada.
- **SLO**: < 5.0s
- **Métrica**: `llm_queue_wait_seconds`.

### Provider Fallback Rate
- **Descrição**: Percentual de requisições que sofreram fallback para um provider secundário.
- **SLO**: < 5%
- **Métrica**: `llm_routing_fallbacks_total`.

### Error Rate
- **Descrição**: Taxa de erros (4xx e 5xx) em relação ao total de requisições.
- **SLO**: < 1%
- **Métrica**: `llm_request_errors_total`.

### Cache Hit Ratio
- **Descrição**: Eficiência do cache de inferência.
- **SLO**: > 20% (alvo desejado)
- **Métrica**: `llm_cache_hits_total` / (`llm_cache_hits_total` + `llm_cache_misses_total`).

### Model Activation Success Rate
- **Descrição**: Taxa de sucesso no carregamento/ativação de modelos (hot-swap).
- **SLO**: 99.9%
- **Métrica**: `llm_model_hot_swap_failures_total`.
