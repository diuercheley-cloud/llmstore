# Enterprise AI Operations Center

Unified command center for governance, workflows, compliance, receipts, attestation, fairness, billing, sovereign runtime, and supervisor AI.

## Architecture

The Operations Center aggregates data from multiple specialized modules:

- **Governance**: Policy enforcement (OPA Rego) and Supervisor AI monitoring.
- **Workflows**: Deterministic DAG execution and replay validation.
- **Compliance**: Automated evidence collection for SOC2, GDPR, HIPAA.
- **Trust**: Hardware-level attestation (TEE/TPM) and cryptographic receipts.
- **Risk**: Real-time risk heatmaps and remediation timelines.
- **Billing**: Anomaly detection and multi-tenant allocation.

## Admin Dashboard (UI/Admin)

Accessible via the `Ops Center` tab in the Admin Dashboard.

### Components:
- **Governance Command Center**: Real-time policy evaluation.
- **Sovereign Operations Map**: Geographic node isolation status.
- **Workflow DAG Explorer**: Deterministic replay visualization.
- **Risk Heatmaps**: Infrastructure and compliance risk scores.
- **Trust Dashboard**: Hardware integrity status.

## Client Portal (UI/Portal)

Accessible via the `Operations Center` menu in the Client Portal.

### Components:
- **Tenant Trust Status**: Verified identity and integrity status.
- **Workflow Audit Explorer**: Detailed audit logs for automated workflows.
- **Signed Receipts Viewer**: Cryptographic proof of execution.
- **Evidence Center**: Downloadable compliance artifacts.

## API Endpoints

All endpoints require admin privileges.

- `GET /admin/ops/overview`: General system health and status.
- `GET /admin/ops/governance`: Policy enforcement metrics.
- `GET /admin/ops/risk`: Aggregated risk scores.
- `GET /admin/ops/workflows`: Workflow execution statistics.
- `GET /admin/ops/receipts`: Cryptographic receipt status.
- `GET /admin/ops/compliance`: Evidence collection status.
- `GET /admin/ops/attestation`: Hardware integrity status.

## Security

- **RBAC**: Strict access control via admin tokens.
- **Tenant Isolation**: Data filtered by tenant ID in the Portal view.
- **Audit Logs**: Immutable access logs for all Ops Center operations.
