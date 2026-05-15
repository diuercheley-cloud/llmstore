# Commercial Distributed Analytics

## Objetivo

Adicionar analytics distribuido multi-node para commercial routing sem depender de Redis/Kafka novos, mantendo single-node funcional e tratando analytics como best-effort.

## Identidade do Node

- `NODE_ID`: quando definido, vira a identidade persistida do node.
- `NODE_ID` vazio: o sistema gera um id deterministico a partir de `hostname + NODE_ROLE + process id`.
- `NODE_ROLE`: `api`, `worker`, `scheduler`, `router` ou `unknown`.
- `CLUSTER_ID`: identificador logico do cluster exibido no dashboard e exports.

## Heartbeat

- Persistido em `commercial_node_heartbeats`.
- Atualiza `last_seen_at` sem derrubar a API se o banco falhar.
- `COMMERCIAL_NODE_HEARTBEAT_INTERVAL_SECONDS` controla a frequencia.
- `COMMERCIAL_NODE_OFFLINE_AFTER_SECONDS` controla quando um node vira `offline`.
- Status intermediario `degraded` aparece antes do timeout final.

## Ingest

- Persistido em `commercial_routing_event_ingest`.
- Aceita eventos de varios nodes para o mesmo banco.
- O evento comercial principal continua em `commercial_routing_events`.
- No modo distribuido, a gravacao principal segue igual e um ingest auxiliar e criado em best-effort.
- Falha de ingest nao derruba a request principal.

## Dedupe

- A chave de dedupe usa `event_id`, `correlation_id` e `request_id`.
- Repeticoes vao para `status=duplicate`.
- Se o ingest aponta para um `commercial_routing_event_id` ja persistido no mesmo node, ele vira `processed` e nao duplica o evento real.
- Nunca gravamos prompts, responses ou secrets no payload persistido.

## Aggregates

- Persistidos em `commercial_cluster_aggregates`.
- Bucket configuravel por `COMMERCIAL_ANALYTICS_AGGREGATION_BUCKET_MINUTES`.
- Consolida por `node`, `provider`, `model` e `client`.
- O cluster overview exposto pela API inclui:
  - requests
  - revenue/cost/margin
  - fallback/block
  - error count
  - avg latency
  - drift estimado vs atual
  - anomalias cross-node

## Retention

- `COMMERCIAL_ANALYTICS_RETENTION_DAYS` controla limpeza de:
  - `commercial_routing_event_ingest`
  - `commercial_cluster_aggregates`
  - `commercial_node_heartbeats`
- `commercial_routing_events` nao e apagado por esse cleanup.

## Endpoints

- `GET /admin/routing/distributed/nodes`
- `GET /admin/routing/distributed/cluster-overview`
- `GET /admin/routing/distributed/aggregates`
- `POST /admin/routing/distributed/ingest`
- `POST /admin/routing/distributed/rebuild-aggregates`
- `POST /admin/routing/distributed/cleanup`
- `GET /admin/routing/distributed/export?format=json|csv|html`

Todos exigem `X-Admin-Token`.

## Dashboard

O admin UI ganhou a secao **Cluster Analytics** com:

- `cluster_id`
- nodes healthy/degraded/offline
- requests e margem por node
- fallback/block por node
- provider usage cross-node
- aggregates por bucket
- ultimo heartbeat
- botoes de rebuild e cleanup

## Limites

- Consistencia eventual, nao transacional entre nodes.
- O overview reprocessa pendencias antes de recalcular buckets, mas ainda depende do banco compartilhado.
- Sem leader election: multiplos nodes podem rodar o loop periodico ao mesmo tempo, com operacoes idempotentes/best-effort.

## Troubleshooting

- Node nao aparece: valide `COMMERCIAL_DISTRIBUTED_ANALYTICS_ENABLED=true`, `NODE_ROLE` e conectividade com o banco.
- Todos offline: cheque `COMMERCIAL_NODE_OFFLINE_AFTER_SECONDS` e erros de escrita no banco.
- Aggregates zerados: rode `POST /admin/routing/distributed/rebuild-aggregates`.
- Duplicate alto: revise emissores que reenviam o mesmo `correlation_id` ou `request_id`.
- Secrets redacted: comportamento esperado; payload bruto nao deve ser persistido.
