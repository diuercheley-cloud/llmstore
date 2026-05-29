---
owner: platform-ops
status: consolidated
---

# Deterministic Workflows

Fase 55 adiciona um orquestrador determinístico de workflows AI multi-stage com DAGs verificáveis, checkpoints reproduzíveis, receipts de pipeline e lineage criptográfico ponta a ponta.

## Componentes

- `CommercialWorkflowDefinition`: blueprint imutável do DAG, com `definition_hash`, `dag_json` e compatibilidade offline.
- `CommercialWorkflowExecution`: execução isolada por tenant, com `dag_hash`, `execution_hash_chain`, `ledger_hash`, `provenance_hash` e suporte a pause/resume.
- `CommercialWorkflowStage`: estágio materializado, com dependências, hashes determinísticos, gates de policy e lineage.
- `CommercialWorkflowCheckpoint`: snapshot reproduzível e assinado, encadeado por `previous_checkpoint_hash`.
- `CommercialWorkflowReceipt`: recibo sanitizado do pipeline, assinado e encadeado por tenant.

## Serviços

- `app/services/workflows/deterministic_orchestrator.py`: engine de DAG, execução determinística, policy gates, rollback seguro e replay-safe orchestration.
- `app/services/workflows/checkpoint_replay.py`: criação, validação, rollback e export de checkpoints.
- `app/services/workflows/workflow_receipts.py`: emissão, export e verificação de receipts.
- `app/services/workflows/workflow_provenance.py`: provenance summary, lineage e drift detection.

## Integrações

- Trusted Agent Runtime: estágios `agent_tool` podem derivar hashes de plano confiável.
- Cryptographic Receipts: receipts de workflow seguem cadeia SHA-256 com assinatura destacada placeholder.
- Policy Governance: gates por estágio suportam allow, deny e approval required.
- Governance Federation: metadados de execução registram readiness de federação.
- Confidential Runtime: estágios podem registrar auditoria confidencial sem logs plaintext.
- Sovereign Appliance Mode: execuções podem carregar `offline_bundle_hash` e gerar manifests offline.

## APIs

- `GET|POST /admin/workflows/definitions`
- `GET|POST /admin/workflows/executions`
- `POST /admin/workflows/executions/{id}/stages/{stage_key}`
- `POST /admin/workflows/executions/{id}/pause`
- `POST /admin/workflows/executions/{id}/resume`
- `POST /admin/workflows/executions/{id}/rollback`
- `GET /admin/workflows/executions/{id}/provenance`
- `GET /admin/workflows/executions/{id}/checkpoints`
- `POST /admin/workflows/replay/{execution_id}`
- `POST /admin/workflows/replay/{replay_id}/attach/{replay_execution_id}`
- `POST /admin/workflows/replay/{replay_id}/verify`
- `GET|POST /admin/workflows/receipts/*`
- `GET /portal/workflows/audit/executions`
- `GET /portal/workflows/audit/receipts`
- `GET /portal/workflows/audit/provenance/{execution_id}`
- `GET /portal/workflows/audit/determinism/{execution_id}`

Os endpoints legados em `/admin/inference/workflows/*` continuam expostos para compatibilidade.

## Segurança

- SHA-256 obrigatório em definição, estágio, checkpoint, ledger e receipt.
- Sem logs plaintext de payload sensível: campos suspeitos são exportados como hash.
- Isolamento multi-tenant por `tenant_id` na execução, estágio e receipt.
- Checkpoints assinados e encadeados.
- Exports sanitizados por padrão.

## Limites

- O sistema implementa verificabilidade prática e replay determinístico operacional.
- Não promete prova formal matemática completa.
- A assinatura atual é `ed25519_placeholder`, coerente com o restante da stack.

## Validação

Use:

```bash
make validate-deterministic-workflows
```
