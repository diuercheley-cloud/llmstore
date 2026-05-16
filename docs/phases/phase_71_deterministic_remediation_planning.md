# Phase 71: Deterministic Remediation Planning

## Overview
Phase 71 introduces a deterministic mechanism for generating operational remediation plans. These plans are derived from failure forecasts, risk assessments, and operational correlations. 

**Crucial Note:** This phase is strictly for **planning and advisory purposes**. No automatic remediation is executed, and no operational state is altered.

## Objectives
- Generate deterministic remediation plans based on operational inputs.
- Breakdown plans into granular, ordered remediation steps.
- Calculate potential impact and blast radius for each plan.
- Identify approval requirements for future execution.
- Provide cryptographic-ready receipts and audit logs for all planning activities.
- Expose an administrative API and integrate with the dashboard/portal.

## Architectural Principles
1. **Determinism:** The same set of operational inputs will always result in the same logical remediation plan.
2. **Advisory-Only:** Plans are recommendations and do not trigger any automated actions (`advisory_only=True`).
3. **Dry-Run by Default:** All steps and plans are marked as dry-runs (`dry_run=True`).
4. **Tenant Isolation:** All data is strictly scoped to `client_id`.
5. **Auditability:** Every plan proposal and receipt generation is logged in the system audit trail.
6. **Offline-First:** All logic is local and does not depend on external APIs, ML models, or SaaS services.

## Components

### Data Model
- `RemediationPlan`: The root entity representing a proposed remediation strategy.
- `RemediationStep`: Granular actions required to fulfill the plan.
- `RemediationPlanReceipt`: Cryptographic-ready proof of plan generation.
- `RemediationApprovalRequirement`: Declarative requirements for plan approval.

### Services
- `DeterministicRemediationPlanner`: Core engine for generating plans and steps.
- `RemediationBlastRadiusService`: Calculates the potential impact of a plan.
- `RemediationApprovalRequirementService`: Determines necessary approvals.
- `RemediationReceiptService`: Builds deterministic receipts.
- `RemediationAuditService`: Handles operational audit logging.

### API
- `POST /admin/operations/remediation-plans/propose`: Propose a new plan.
- `GET /admin/operations/remediation-plans`: List plans for a client.
- `GET /admin/operations/remediation-plans/{plan_id}`: Get plan details.
- `GET /admin/operations/remediation-plans/{plan_id}/steps`: Get plan steps.
- `GET /admin/operations/remediation-plans/{plan_id}/approvals`: Get approval requirements.
- `POST /admin/operations/remediation-plans/{plan_id}/receipt`: Generate a plan receipt.

## Security & Compliance
- **No Enforcement:** The system explicitly lacks any code to execute the remediation steps.
- **Sanitization:** Input payloads are sanitized before being used in hashes or stored.
- **Signature Placeholders:** Receipts use deterministic hash-based placeholders rather than real cryptographic signatures to maintain offline compatibility while remaining verifiable.
