---
owner: platform-ops
status: consolidated
---

# Catálogo de Métricas Prometheus

Este catálogo lista as métricas padronizadas expostas pelo `llm-inference-stack` para monitoramento e SLOs.

## Requisições e Tráfego
- `llm_requests_total`: Total de requisições tratadas. Labels: `model`, `backend`, `plan`, `endpoint`, `status_code`.
- `llm_request_errors_total`: Total de erros. Labels: `model`, `backend`, `plan`, `endpoint`, `error_type`.
- `llm_request_latency_seconds`: Histograma de latência end-to-end. Labels: `model`, `backend`, `plan`, `endpoint`.

## Tokens e Faturamento
- `llm_tokens_input_total`: Total de tokens de entrada processados.
- `llm_tokens_output_total`: Total de tokens de saída gerados.
- `llm_cost_estimated_brl_total`: Estimativa de custo em BRL. Labels: `model`, `client_id`.

## Filas e QoS
- `llm_queue_wait_seconds`: Tempo de espera em fila. Labels: `plan`.
- `llm_queue_depth`: Profundidade atual da fila. Labels: `plan`.

## Routing e Providers
- `llm_provider_health_score`: Score de saúde do provider (0-1). Labels: `provider_name`.
- `llm_provider_failures_total`: Falhas por provider. Labels: `provider_name`, `error_code`.
- `llm_routing_decisions_total`: Decisões de roteamento tomadas. Labels: `strategy`, `model`.
- `llm_routing_fallbacks_total`: Fallbacks acionados. Labels: `reason`, `model`.

## Cache
- `llm_cache_hits_total`: Hits de cache.
- `llm_cache_misses_total`: Misses de cache.

## Infraestrutura e Runtime
- `llm_gpu_memory_pressure_ratio`: Pressão de memória GPU. Labels: `node_id`, `gpu_id`.
- `llm_model_runtime_active`: Estado ativo de runtimes de modelo. Labels: `model_id`.
- `llm_model_hot_swap_failures_total`: Falhas em trocas a quente de modelos.
- `llm_attestation_failures_total`: Falhas de hardware attestation. Labels: `node_id`, `reason`.

## Segurança
- `llm_rbac_denials_total`: Negativas de acesso RBAC. Labels: `client_id`, `resource`, `action`.
