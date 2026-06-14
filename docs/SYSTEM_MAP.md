---
owner: platform-ops
status: consolidated
---

# System Map: Module Locations

This document maps logical system modules to their physical locations in the codebase.

## 1. Inference & Core API
- **Entry Point**: `control_plane/app/main.py`
- **OpenAI Compatibility**: `control_plane/app/api/public.py`
- **RAG Services**: `control_plane/app/api/rag.py`, `control_plane/app/api/rag_enterprise.py`
- **TTS Services**: `control_plane/app/api/pocket_tts.py`

## 2. Routing Engine
- **Base Routing**: `control_plane/app/api/routing_admin.py`
- **Geo-Routing**: `control_plane/app/api/commercial_geo_routing_admin.py`
- **Global Traffic**: `control_plane/app/api/commercial_global_traffic_admin.py`
- **Cross-Cluster**: `control_plane/app/api/commercial_cross_cluster_forwarding_admin.py`
- **Live Balancing**: `control_plane/app/api/commercial_live_balancing_admin.py`

## 3. QoS & Resource Management
- **QoS Controls**: `control_plane/app/api/commercial_qos_admin.py`
- **Fairness & Priority**: `control_plane/app/services/qos/`
- **Capacity Planning**: `control_plane/app/api/commercial_capacity_admin.py`

## 4. Billing & Financials
- **Prepaid Wallet**: `control_plane/app/api/wallet_admin.py`, `control_plane/app/api/payments.py`
- **BRL/PIX Logic**: `control_plane/app/services/billing/`
- **Reconciliation**: `control_plane/app/api/billing_reconciliation_admin.py`
- **Revenue Protection**: `control_plane/app/api/commercial_revenue_protection_admin.py`

## 5. Security & Trust Chain
- **Tenant Encryption**: `control_plane/app/api/commercial_encryption_admin.py`
- **Model Supply Chain**: `control_plane/app/api/commercial_model_supply_chain_admin.py`
- **Runtime Integrity**: `control_plane/app/services/inference/runtime_integrity.py`
- **Inference Receipts**: `control_plane/app/api/commercial_cryptographic_receipts_admin.py`
- **Merkle Timelines**: `control_plane/app/services/inference/merkle_timelines.py`
- **Execution Proofs**: `control_plane/app/services/inference/execution_proofs.py`
- **Public Verifier**: `tools/public_verifier/`

## 6. Governance & Compliance
- **Governance Federation**: `control_plane/app/api/commercial_governance_federation_admin.py`
- **Policy-as-Code**: `control_plane/app/api/commercial_policy_governance_admin.py`
- **Sovereign Governance**: `control_plane/app/api/commercial_sovereign_governance_admin.py`
- **Compliance Controls**: `control_plane/app/api/commercial_compliance_admin.py`

## 7. Infrastructure & HA
- **HA / Leader Election**: `control_plane/app/api/commercial_ha_admin.py`
- **Infra Execution**: `control_plane/app/api/commercial_infra_admin.py`
- **Simulation**: `control_plane/app/services/infra/simulation.py`

## 8. Frontend & Portals
- **Admin Dashboard**: `frontend/admin/` (Route: `/admin`)
- **Client Portal**: `frontend/client/` (Route: `/`)
- **Legacy Mounts**: `control_plane/app/static/` (Route: `/static/*`, **Disabled by default**)
- **Enterprise Audit**: `control_plane/app/static/enterprise-audit/` (Disabled)

## 9. Tools & Utilities
- **CLI Verifier**: `tools/public_verifier/verifier_cli.py`
- **Validation Scripts**: `scripts/*.sh`
- **Database Migrations**: `control_plane/alembic/versions/`

---

**Next Steps**: See [PHASE_INDEX.md](PHASE_INDEX.md) for the historical progression of the platform.
