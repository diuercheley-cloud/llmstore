---
owner: platform-ops
status: consolidated
---

# Domain Boundaries

## Regras Gerais

- Dependencias diretas entre planes sao excecao, nao regra.
- Integracao entre planes deve preferir eventos, registros persistidos e contratos de leitura estaveis.
- `app.core`, `app.db`, `app.models`, `app.schemas` e `app.utils` sao camadas compartilhadas permitidas.
- O validador desta fase aplica apenas um subconjunto minimo de imports proibidos para nao quebrar compatibilidade atual.

## Runtime Fabric

Responsabilidades:
- roteamento, cache, filas, providers, workflows deterministicos, healing/recovery de runtime

Pode importar:
- shared layers
- modulos internos do proprio `Runtime Fabric`
- interfaces estaveis expostas por `Governance`, `Trust`, `Financial` e `Sovereign` quando necessario para execucao atual

Nao pode acessar diretamente:
- operator portals do `Operations Plane`
- superficies administrativas que nao participam da execucao

Eventos permitidos:
- `runtime.degradation_detected`
- `runtime.failure_detected`
- `runtime.recovery_requested`
- `runtime.workflow_replay_requested`
- `runtime.capacity_changed`

## Governance Plane

Responsabilidades:
- policy registry, policy evaluation, explainability, governance federation, blast radius analysis, approval gates

Pode importar:
- shared layers
- modulos internos do proprio `Governance Plane`
- componentes do `Runtime Fabric` e `Trust Plane` estritamente necessarios para policy evaluation atual
- componentes do `Financial Plane` apenas via controles financeiros ja existentes

Nao pode acessar diretamente:
- operator surfaces do `Operations Plane`
- mesh soberano fora de contratos de sync/policy

Eventos permitidos:
- `governance.policy_published`
- `governance.policy_activated`
- `governance.approval_required`
- `governance.approval_granted`
- `governance.blast_radius_assessed`

## Trust Plane

Responsabilidades:
- KMS runtime, signing, attestation, receipts, replay verification, trust graph, trust snapshots

Pode importar:
- shared layers
- modulos internos do proprio `Trust Plane`
- componentes do `Runtime Fabric` necessarios para gerar provas e correlacionar execucao
- trilhas financeiras imutaveis estritamente necessarias para audit trail

Nao pode acessar diretamente:
- policy authoring do `Governance Plane`
- operator surfaces do `Operations Plane`
- mecanismos soberanos de sincronizacao manual

Eventos permitidos:
- `trust.receipt_issued`
- `trust.signature_verified`
- `trust.attestation_failed`
- `trust.integrity_drift_detected`
- `trust.violation_detected`

## Financial Plane

Responsabilidades:
- pricing, wallet, billing, reconciliation, disputes, anomaly detection, revenue protection

Pode importar:
- shared layers
- modulos internos do proprio `Financial Plane`
- componentes do `Runtime Fabric` para export/reporting operacional ja existente
- componentes do `Trust Plane` para encryption e trilha auditavel

Nao pode acessar diretamente:
- policy engines do `Governance Plane`
- operator surfaces do `Operations Plane`
- mesh e appliance internals do `Sovereign Plane`

Eventos permitidos:
- `financial.charge_recorded`
- `financial.wallet_debited`
- `financial.reconciliation_mismatch_detected`
- `financial.dispute_opened`
- `financial.revenue_escalation_triggered`

## Sovereign Plane

Responsabilidades:
- appliance mode, airgap sync, mesh soberano, failover soberano, restricoes de residencia e export/import offline

Pode importar:
- shared layers
- modulos internos do proprio `Sovereign Plane`
- componentes do `Runtime Fabric` e `Trust Plane` necessarios para operar em modo soberano

Nao pode acessar diretamente:
- operator portals do `Operations Plane`
- billing e dispute internals do `Financial Plane`

Eventos permitidos:
- `sovereign.sync_manifest_created`
- `sovereign.sync_manifest_applied`
- `sovereign.partition_detected`
- `sovereign.airgap_policy_enforced`
- `sovereign.mesh_failover_started`

## Operations Plane

Responsabilidades:
- audit portals, exports, operator observability, administrative support surfaces, runbook-oriented tooling

Pode importar:
- shared layers
- modulos internos do proprio `Operations Plane`
- componentes do `Runtime Fabric`, `Trust` e `Financial` estritamente para leitura, exportacao e operacao

Nao pode acessar diretamente:
- policy engines do `Governance Plane`
- appliance internals e mesh internals do `Sovereign Plane`

Eventos permitidos:
- `operations.audit_export_requested`
- `operations.report_generated`
- `operations.operator_action_logged`
- `operations.incident_opened`
- `operations.readiness_snapshot_recorded`

## Imports Proibidos Enforced Nesta Fase

O validador estatico desta fase reprova imports diretos entre os seguintes pares:

- `Financial Plane -> Governance Plane`
- `Financial Plane -> Operations Plane`
- `Financial Plane -> Sovereign Plane`
- `Operations Plane -> Governance Plane`
- `Operations Plane -> Sovereign Plane`
- `Trust Plane -> Governance Plane`
- `Trust Plane -> Operations Plane`
- `Trust Plane -> Sovereign Plane`
- `Sovereign Plane -> Financial Plane`
- `Sovereign Plane -> Operations Plane`

Essas regras foram escolhidas porque:

- preservam compatibilidade da base atual
- bloqueiam novos acoplamentos de maior risco antes das fases 66-68
- mantem o enforcement simples e offline-first
