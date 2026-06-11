<!-- AUTO-GENERATED: do not edit manually -->
<!-- Last updated: 2026-06-11 -->

# Deprecated Surface Inventory

Inventário completo de superfícies deprecated, duplicadas ou sem dono.

## Legenda

| Campo | Descrição |
|---|---|
| `item` | Nome ou caminho do item |
| `tipo` | Categoria: `api`, `capability`, `feature_flag`, `python_module`, `cli_param`, `shim`, `doc`, `script` |
| `status` | `deprecated`, `legacy`, `orphaned`, `unowned` |
| `owner` | Time responsável |
| `substituto` | Caminho de migração ou substituto |
| `última evidência de uso` | Referência mais recente conhecida |
| `plano de remoção` | Prazo ou versão alvo para remoção |

---

## 1. API Endpoints Deprecated

### 1.1 `/admin/billing/*` (64 endpoints)

| Item | Tipo | Status | Owner | Substituto | Última evidência de uso | Plano de remoção |
|---|---|---|---|---|---|---|
| `GET /admin/billing/anomalies` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 (sunset default) | v3.0 / 2026-12-31 |
| `POST /admin/billing/anomalies/run` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `POST /admin/billing/anomalies/{anomaly_id}/ack` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `POST /admin/billing/anomalies/{anomaly_id}/ignore` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `POST /admin/billing/anomalies/{anomaly_id}/resolve` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `GET /admin/billing/audit/validate-chain` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `GET /admin/billing/clients/{client_id}/invoice/preview` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `GET /admin/billing/disputes` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `POST /admin/billing/disputes/manual-credit` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `POST /admin/billing/disputes/{id}/reject` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `POST /admin/billing/disputes/{id}/resolve` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `POST /admin/billing/disputes/{id}/review` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `GET /admin/billing/forecast/overview` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `GET /admin/billing/forecast/records` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `POST /admin/billing/forecast/run` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `GET /admin/billing/invoices` | api | deprecated | billing-ops | `/admin/commercial/billing` | test_surface_consolidation.py:8 | v3.0 / 2026-12-31 |
| `POST /admin/billing/invoices/generate` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `GET /admin/billing/invoices/preview` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `PATCH /admin/billing/invoices/{invoice_id}/cancel` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `PATCH /admin/billing/invoices/{invoice_id}/mark-overdue` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `PATCH /admin/billing/invoices/{invoice_id}/mark-paid` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `GET /admin/billing/margins/summary` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `GET /admin/billing/payments` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `POST /admin/billing/payments` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `PATCH /admin/billing/payments/{payment_id}/cancel` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `GET /admin/billing/plans` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `POST /admin/billing/plans` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `PATCH /admin/billing/plans/{plan_id}` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `PATCH /admin/billing/plans/{plan_id}/models` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `GET /admin/billing/pricing-rules` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `POST /admin/billing/pricing/simulate` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `GET /admin/billing/provider-costs` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `GET /admin/billing/qos/export` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `POST /admin/billing/qos/generate` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `GET /admin/billing/qos/overview` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `GET /admin/billing/qos/records` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `POST /admin/billing/qos/{record_id}/attach-invoice` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `POST /admin/billing/qos/{record_id}/debit-wallet` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `GET /admin/billing/reconciliation/mismatches` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `GET /admin/billing/reconciliation/overview` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `POST /admin/billing/reconciliation/run` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `POST /admin/billing/reconciliation/{id}/resolve` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `GET /admin/billing/revenue-escalations/deliveries` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `GET /admin/billing/revenue-escalations/policies` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `POST /admin/billing/revenue-escalations/policies` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `PATCH /admin/billing/revenue-escalations/policies/{policy_id}` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `POST /admin/billing/revenue-escalations/retry/{delivery_id}` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `GET /admin/billing/revenue-escalations/status` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `POST /admin/billing/revenue-escalations/test` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `GET /admin/billing/revenue-protection/actions` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `POST /admin/billing/revenue-protection/actions/{action_id}/apply` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `POST /admin/billing/revenue-protection/actions/{action_id}/revert` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `POST /admin/billing/revenue-protection/evaluate` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `GET /admin/billing/revenue-protection/policies` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `POST /admin/billing/revenue-protection/policies` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `PATCH /admin/billing/revenue-protection/policies/{policy_id}` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `GET /admin/billing/revenue-protection/status` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `POST /admin/billing/run-cycle` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `GET /admin/billing/usage-financials` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `GET /admin/billing/wallets` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `GET /admin/billing/wallets/{client_id}` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `POST /admin/billing/wallets/{client_id}/adjustment` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `POST /admin/billing/wallets/{client_id}/manual-credit` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |
| `GET /admin/billing/wallets/{client_id}/transactions` | api | deprecated | billing-ops | `/admin/commercial/billing` | middleware.py:219 | v3.0 / 2026-12-31 |

### 1.2 `/admin/models/runtime/*` (6 endpoints)

| Item | Tipo | Status | Owner | Substituto | Última evidência de uso | Plano de remoção |
|---|---|---|---|---|---|---|
| `GET /admin/models/runtime` | api | deprecated | model-ops | `/admin/models/lifecycle` | test_api_surface.py:21 | v3.0 / 2026-12-31 |
| `POST /admin/models/runtime/activate/{instance_id}` | api | deprecated | model-ops | `/admin/models/lifecycle` | middleware.py:219 | v3.0 / 2026-12-31 |
| `POST /admin/models/runtime/load` | api | deprecated | model-ops | `/admin/models/lifecycle` | middleware.py:219 | v3.0 / 2026-12-31 |
| `POST /admin/models/runtime/rollback` | api | deprecated | model-ops | `/admin/models/lifecycle` | middleware.py:219 | v3.0 / 2026-12-31 |
| `POST /admin/models/runtime/unload/{instance_id}` | api | deprecated | model-ops | `/admin/models/lifecycle` | middleware.py:219 | v3.0 / 2026-12-31 |
| `GET /admin/models/runtime/{instance_id}/health` | api | deprecated | model-ops | `/admin/models/lifecycle` | middleware.py:219 | v3.0 / 2026-12-31 |

---

## 2. Capabilities Deprecated

| Item | Tipo | Status | Owner | Substituto | Última evidência de uso | Plano de remoção |
|---|---|---|---|---|---|---|
| `marketplace` (Marketplace legacy) | capability | deprecated | product-team | `agent-marketplace` (beta) | supported-surface.yaml:1561, PRODUCT_SURFACE.md:84 | v3.0 |

---

## 3. Feature Flags Deprecated (40 flags)

All have `remove_after: v2.2.0` and `replacement: consolidated_core_v2`.

| Item | Tipo | Status | Owner | Substituto | Última evidência de uso | Plano de remoção |
|---|---|---|---|---|---|---|
| `AGENT_REMOTE_MARKETPLACE_ENABLED` | feature_flag | deprecated | agent-platform | `consolidated_core_v2` | feature-flags.yaml:312 | v2.2.0 |
| `AGENT_CONNECTOR_TOKEN_STORAGE_ENABLED` | feature_flag | deprecated | agent-platform | `consolidated_core_v2` | feature-flags.yaml:449 | v2.2.0 |
| `AGENT_CONNECTOR_CREDENTIAL_ROTATION_ENABLED` | feature_flag | deprecated | agent-platform | `consolidated_core_v2` | feature-flags.yaml:463 | v2.2.0 |
| `AGENT_WORKFLOW_TIMERS_ENABLED` | feature_flag | deprecated | agent-platform | `consolidated_core_v2` | feature-flags.yaml:608 | v2.2.0 |
| `AGENT_WORKFLOW_DISTRIBUTED_LOCKS_ENABLED` | feature_flag | deprecated | agent-platform | `consolidated_core_v2` | feature-flags.yaml:646 | v2.2.0 |
| `CI_DEPLOY_ENABLED` | feature_flag | deprecated | platform-ops | `consolidated_core_v2` | feature-flags.yaml:1176 | v2.2.0 |
| `COMMERCIAL_ANALYTICS_DEDUPE_ENABLED` | feature_flag | deprecated | platform-ops | `consolidated_core_v2` | feature-flags.yaml:1238 | v2.2.0 |
| `COMMERCIAL_CALIBRATION_ENABLED` | feature_flag | deprecated | platform-ops | `consolidated_core_v2` | feature-flags.yaml:1290 | v2.2.0 |
| `COMMERCIAL_CROSS_CLUSTER_FORWARDING_CIRCUIT_BREAKER_ENABLED` | feature_flag | deprecated | platform-ops | `consolidated_core_v2` | feature-flags.yaml:1402 | v2.2.0 |
| `COMMERCIAL_CROSS_CLUSTER_FORWARDING_ENABLED` | feature_flag | deprecated | platform-ops | `consolidated_core_v2` | feature-flags.yaml:1414 | v2.2.0 |
| `COMMERCIAL_EXECUTIVE_DASHBOARD_ENABLED` | feature_flag | deprecated | platform-ops | `consolidated_core_v2` | feature-flags.yaml:1486 | v2.2.0 |
| `COMMERCIAL_FINANCIAL_ANOMALY_DETECTION_ENABLED` | feature_flag | deprecated | platform-ops | `consolidated_core_v2` | feature-flags.yaml:1528 | v2.2.0 |
| `COMMERCIAL_FINANCIAL_AUDIT_CHAIN_ENABLED` | feature_flag | deprecated | platform-ops | `consolidated_core_v2` | feature-flags.yaml:1540 | v2.2.0 |
| `COMMERCIAL_FINANCIAL_DISPUTE_ENABLED` | feature_flag | deprecated | platform-ops | `consolidated_core_v2` | feature-flags.yaml:1552 | v2.2.0 |
| `COMMERCIAL_MODEL_LIFECYCLE_ENABLED` | feature_flag | deprecated | platform-ops | `consolidated_core_v2` | feature-flags.yaml:1937 | v2.2.0 |
| `COMMERCIAL_POLICY_DRIFT_DETECTION_ENABLED` | feature_flag | deprecated | platform-ops | `consolidated_core_v2` | feature-flags.yaml:2049 | v2.2.0 |
| `COMMERCIAL_POLICY_GOVERNANCE_ENABLED` | feature_flag | deprecated | platform-ops | `consolidated_core_v2` | feature-flags.yaml:2061 | v2.2.0 |
| `COMMERCIAL_POLICY_REQUIRE_APPROVAL_FOR_ENFORCE` | feature_flag | deprecated | platform-ops | `consolidated_core_v2` | feature-flags.yaml:2073 | v2.2.0 |
| `COMMERCIAL_POLICY_REQUIRE_SIGNATURE` | feature_flag | deprecated | platform-ops | `consolidated_core_v2` | feature-flags.yaml:2085 | v2.2.0 |
| `COMMERCIAL_QOS_CHARGEBACK_ENABLED` | feature_flag | deprecated | platform-ops | `consolidated_core_v2` | feature-flags.yaml:2167 | v2.2.0 |
| `COMMERCIAL_QOS_FAIRNESS_ENABLED` | feature_flag | deprecated | platform-ops | `consolidated_core_v2` | feature-flags.yaml:2179 | v2.2.0 |
| `COMMERCIAL_REVENUE_FORECASTING_ENABLED` | feature_flag | deprecated | platform-ops | `consolidated_core_v2` | feature-flags.yaml:2402 | v2.2.0 |
| `COMMERCIAL_TRANSPARENCY_GOSSIP_ENABLED` | feature_flag | deprecated | platform-ops | `consolidated_core_v2` | feature-flags.yaml:2564 | v2.2.0 |
| `COMMERCIAL_WITNESS_FEDERATION_ENABLED` | feature_flag | deprecated | platform-ops | `consolidated_core_v2` | feature-flags.yaml:2576 | v2.2.0 |
| `COMPLIANCE_AUDIT_PACKAGE_ENABLED` | feature_flag | deprecated | platform-ops | `consolidated_core_v2` | feature-flags.yaml:2608 | v2.2.0 |
| `COMPLIANCE_EVIDENCE_COLLECTION_ENABLED` | feature_flag | deprecated | platform-ops | `consolidated_core_v2` | feature-flags.yaml:2620 | v2.2.0 |
| `COMPLIANCE_EXTERNAL_EXPORT_ENABLED` | feature_flag | deprecated | platform-ops | `consolidated_core_v2` | feature-flags.yaml:2632 | v2.2.0 |
| `COMPLIANCE_READINESS_ENABLED` | feature_flag | deprecated | platform-ops | `consolidated_core_v2` | feature-flags.yaml:2644 | v2.2.0 |
| `AGENT_PROVIDER_VALIDATION_ENABLED` (legacy alias) | feature_flag | deprecated | - | `AGENT_REAL_PROVIDER_VALIDATION_ENABLED` | feature-flags.yaml:3075 | v2.1.0 |

*(11 additional deprecated COMMERCIAL_* flags at lines 1574-1937 with same `remove_after: v2.2.0`)*

---

## 4. Python Modules Deprecated

| Item | Tipo | Status | Owner | Substituto | Última evidência de uso | Plano de remoção |
|---|---|---|---|---|---|---|
| `scripts/llm_harness/agent_harness.py` | python_module | deprecated | agent-platform | `scripts.llm_harness.cli` | agent_harness.py:1-5 docstring | v3.0 |
| `control_plane/.../disaster_recovery/agent_backup.py` (AgentBackupService) | python_module | deprecated | platform-ops | `BackupService` c/ `scope=logical-agent-backup` | agent_backup.py:4, docs/BACKUP_ARCHITECTURE.md | v3.0 (deprecated since v2.4) |
| `control_plane/.../disaster_recovery/agent_backup.py` (BackupScheduler) | python_module | deprecated | platform-ops | Cron + `llmstack backup --logical-agent-backup` | agent_backup.py:277 | v3.0 (deprecated since v2.4) |

---

## 5. CLI Parameters Deprecated

| Item | Tipo | Status | Owner | Substituto | Última evidência de uso | Plano de remoção |
|---|---|---|---|---|---|---|
| `llmstack backup --full` | cli_param | deprecated | platform-ops | `--logical-agent-backup` | stack_cli.py:42 | v3.0 |
| `run_harness()` individual params | api (python) | deprecated | agent-platform | `run_harness(HarnessConfig(...))` | legacy_runner.py:82 | v3.0 |

---

## 6. Deprecation Shims

| Item | Tipo | Status | Owner | Substituto | Última evidência de uso | Plano de remoção |
|---|---|---|---|---|---|---|
| `GET /static/admin` em main.py | shim | deprecated | platform-ops | `/admin` (new dashboard) | main.py:30-34 | v3.0 |
| `deprecation_middleware` em middleware.py | shim | deprecated | platform-ops | Replaced by surface_audit | middleware.py:193-239 | v3.0 |
| `/agents` header `Deprecation: true` injection | shim | deprecated | platform-ops | Migrate to new agent routes | middleware.py:236-237 | v3.0 |

---

## 7. Documentação no Arquivo de Deprecados

| Item | Tipo | Status | Owner | Substituto | Última evidência de uso | Plano de remoção |
|---|---|---|---|---|---|---|
| `docs/archive/deprecated/MIGRATION_POLICY.md` | doc | archived | platform-ops | Consolidado na baseline | docs/archive/deprecated/ | N/A (consolidated) |
| `docs/archive/deprecated/MIGRATION_INDEX.md` | doc | archived | platform-ops | Consolidado na baseline | docs/archive/deprecated/ | N/A (consolidated) |
| `docs/archive/deprecated/LOCALHOST.md` | doc | archived | platform-ops | Consolidado em docs/operations/ | docs/archive/deprecated/ | N/A (consolidated) |
| `docs/archive/deprecated/MIGRATIONS_SQUASH.md` | doc | archived | platform-ops | Squash concluído | docs/archive/deprecated/ | N/A (consolidated) |
| `docs/API_DEPRECATIONS.md` | doc | active | platform-ops | Manter como SOT | docs/API_DEPRECATIONS.md | Manter |

---

## 8. Orphaned / Unowned Surfaces

| Item | Tipo | Status | Owner | Substituto | Última evidência de uso | Plano de remoção |
|---|---|---|---|---|---|---|
| `docs/archive/orphaned_doc_*.md` (99 files) | doc | orphaned | N/A | N/A | docs/archive/ | Revisar e arquivar |
| Endpoints unclassified em API_SURFACE.md | api | unowned | unknown | N/A | docs/generated/API_SURFACE.md | Classificar ou remover |

---

## Sumário

| Tipo | Total | Com plano de remoção | Sem plano |
|---|---|---|---|
| API endpoints deprecated | 70 | 70 | 0 |
| Capabilities deprecated | 1 | 1 | 0 |
| Feature flags deprecated | 40 | 40 | 0 |
| Python modules deprecated | 3 | 3 | 0 |
| CLI params deprecated | 2 | 2 | 0 |
| Shims | 3 | 3 | 0 |
| Archived docs | 4 | 0 | 4 |
| Orphaned docs | 99 | 0 | 99 |
| **Total** | **222** | **119** | **103** |
