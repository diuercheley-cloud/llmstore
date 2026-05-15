# Commercial Federation

Fase 15 adiciona federação multi-cluster para commercial routing sem quebrar o modo single-cluster. Cada cluster continua independente, exporta aggregates comerciais locais e pode consolidar visão federada de requests, custo, margem, latência e anomalias.

## Arquitetura

- `commercial_cluster_registry`: registry administrativo dos clusters conhecidos.
- `commercial_federated_aggregates`: aggregates recebidos de outros clusters com dedupe por bucket e escopo.
- `commercial_cluster_sync_logs`: trilha de sync push/manual, incluindo duplicados e falhas.
- `commercial_cluster_aggregates`: continua sendo a fonte local. A visão federada soma local + federado.

## Modos

- `disabled`: padrão. Não faz comunicação externa.
- `local_only`: mostra apenas o cluster local na visão federada.
- `pull`: reservado para evolução futura; nesta fase não inicia comunicação externa automática.
- `push`: permite envio do export local para peers registrados.
- `hybrid`: igual a `push` nesta fase, preservando metadados para evolução futura.

## Shared Token

- `COMMERCIAL_FEDERATION_REQUIRE_TOKEN=true` exige `X-Federation-Token` no endpoint de ingest.
- `COMMERCIAL_FEDERATION_SHARED_TOKEN` nunca é retornado por endpoints, exports ou dashboard.
- Se `REQUIRE_TOKEN=true`, ingest sem token ou com token inválido retorna `401`.

## Tenant Scope

- Cada cluster pode declarar `tenant_scope_json`.
- Formato suportado:

```json
{
  "tenants": ["tenant-a", "tenant-b"],
  "allow_untagged": false
}
```

- Aggregate fora do escopo é rejeitado.
- Sem escopo configurado: apenas aggregates sem `tenant_id` são aceitos, exceto no cluster local / modo `local_only`.

## Dedupe

- `dedupe_key = source_cluster_id + bucket_start + provider + model + client_id + tenant_id`
- Reenvios do mesmo aggregate não duplicam linhas.
- Sync logs marcam `duplicate` quando o payload já foi visto.

## Endpoints

- `GET /admin/routing/federation/clusters`
- `POST /admin/routing/federation/clusters`
- `GET /admin/routing/federation/overview`
- `GET /admin/routing/federation/compare`
- `GET /admin/routing/federation/export?format=json|csv|html`
- `POST /admin/routing/federation/ingest`
- `POST /admin/routing/federation/sync/manual`
- `POST /admin/routing/federation/cleanup`

## Export

- `json`: overview, clusters, aggregates, comparação e anomalias.
- `csv`: foco em aggregates consolidados.
- `html`: resumo executivo federado.
- PDF não é obrigatório nesta fase.

## Dashboard

O admin dashboard ganhou a seção `Federation` com:

- clusters registrados
- status, região e ambiente
- requests e margem por cluster
- providers por cluster
- comparação cross-cluster
- anomalias
- botões de export, manual sync e cleanup

## Limitações

- Não move tráfego automaticamente entre clusters.
- `pull` fica reservado para evolução posterior, porque os endpoints de export permanecem protegidos por admin token.
- Não exige cloud, Redis extra ou Kafka.
- Não altera endpoints OpenAI-compatible.

## Troubleshooting

- `401 invalid federation token`: confira `COMMERCIAL_FEDERATION_REQUIRE_TOKEN` e `COMMERCIAL_FEDERATION_SHARED_TOKEN`.
- Overview vazio: confirme se o cluster local tem `commercial_cluster_aggregates` ou se houve ingest federado válido.
- Aggregate rejeitado: revise `tenant_scope_json` do cluster de origem.
- Sync manual sem efeito: verifique `COMMERCIAL_FEDERATION_MODE` e `COMMERCIAL_FEDERATION_ALLOW_PUSH`.
