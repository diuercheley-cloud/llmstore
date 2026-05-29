---
owner: platform-ops
status: consolidated
---

# Phase 18: Safe Cross-Cluster HTTP Forwarding Opt-in

## Visão Geral
O Cross-Cluster HTTP Forwarding permite que a camada de controle roteie requisições de inferência diretamente para outro cluster em vez de processá-las localmente. Esse recurso é a base de execução técnica para o *Global Traffic Shifting* (Phase 17), onde uma política canary ou de live balancing decide enviar o tráfego para fora do cluster local.

Esse sistema foi desenhado com segurança máxima: se qualquer erro de rede, SSL ou timeout ocorrer, a requisição sofre *fallback* imediato, de forma invisível para o cliente, caindo na rota local de inferência.

## Arquitetura de Roteamento

1. **Client Endpoint (`/v1/chat/completions`)**: O request chega no control plane local.
2. **Global Traffic Shifter**: Decide se deve rotear (ex: via hash de Canary percentual). Se "sim", retorna `target_cluster_id`.
3. **Cross Cluster Forwarder**: Verifica se o `target_cluster` é elegível e saudável via `CommercialClusterRegistry`.
4. **Circuit Breaker**: Verifica o estado (`closed`, `open`, `half_open`) para não inundar clusters mortos e evitar timeouts em série.
5. **Proxy HTTP**: Usa `httpx.AsyncClient` para forwarder a request (streamed via `yield` chunk a chunk ou raw body).
6. **Fallback de Segurança**: Se o target cluster falhar por HTTP 500, Timeout ou quebra de conexão mTLS/JWT, o erro é engolido, marca falha no Circuit Breaker, e a execução contínua no proxy local (`_chat_with_fallback`).

## Segurança e Privacidade (MANDATÓRIO)
- **Não loga prompts ou completions**: O proxy repassa os binários (bytes) da requisição nativa sem tentar decodificar a carga principal nos logs.
- **Autorização Local Restrita**: O header `Authorization` contendo a chave API do cliente final **NUNCA** é repassado ao cluster remoto. Em vez disso, o proxy local o substitui por um `x-internal-forwarding-auth` contendo um JWT de federação (assinado assimetricamente ou via symmetric secret entre a federação).
- **Sem state mutation em proxy**: O target de proxy só roda inferência, os tokens deduzidos na wallet/faturamento ocorrem no cluster de origem.

## Configurações de Ambiente

| Variável | Padrão | Descrição |
|----------|---------|------------|
| `COMMERCIAL_CROSS_CLUSTER_FORWARDING_ENABLED` | `False` | Habilita todo o framework de forwarding cross-cluster. |
| `COMMERCIAL_CROSS_CLUSTER_FORWARDING_MODE` | `disabled` | Pode ser `dry_run` ou `forwarding`. Em dry run simula e loga success local. |
| `COMMERCIAL_CROSS_CLUSTER_FORWARDING_TIMEOUT_SECONDS` | `2` | Timeout de connect/read para requests sem stream. |
| `COMMERCIAL_CROSS_CLUSTER_FORWARDING_STREAM_TIMEOUT_SECONDS` | `30` | Timeout estendido para SSE streaming (visto que demora para gerar o primeiro chunk e todo o stream). |
| `COMMERCIAL_CROSS_CLUSTER_FORWARDING_REQUIRE_JWT` | `True` | Se repassa um JWT interno de autenticação gerado na hora via `generate_internal_jwt`. |
| `COMMERCIAL_CROSS_CLUSTER_FORWARDING_CIRCUIT_BREAKER_ENABLED`| `True` | Habilita breaker em memória por target id. |
| `COMMERCIAL_CROSS_CLUSTER_FORWARDING_CIRCUIT_BREAKER_FAILURE_THRESHOLD`| `5` | Quantidade de falhas para abrir o breaker. |

## Endpoints de Administração

- `GET /admin/routing/cross-cluster-forwarding/status`: Consulta settings ativos.
- `GET /admin/routing/cross-cluster-forwarding/circuit-breakers`: Consulta status dos breakers (abertos, número de falhas).
- `POST /admin/routing/cross-cluster-forwarding/reset-circuit-breaker?cluster_id=X`: Reseta manual do breaker.
- `POST /admin/routing/cross-cluster-forwarding/test?cluster_id=X`: Realiza verificação sintética e build de headers (dry-run handshake).

## Métricas
Foi adicionado o modelo DB `CommercialCrossClusterForwardingEvent` (que futuramente pode ser agregado ou exportado via metrics prometheus) armazenando: `latency_ms`, `bytes_out`, `bytes_in`, `result: forwarded | fallback_local | blocked`, além de cluster source/target.
