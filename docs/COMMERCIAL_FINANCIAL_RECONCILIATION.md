---
owner: platform-ops
status: consolidated
---

# Commercial Financial Reconciliation & Dispute Management (Phase 27)

## Overview

Phase 27 introduces automated financial reconciliation, dispute management, and an immutable financial audit trail to the LLM Inference Stack. These features ensure financial integrity by detecting discrepancies between different billing layers and providing a structured process for handling client disputes.

## Financial Reconciliation

Reconciliation is the process of comparing records across different layers of the system to ensure they match.

### Reconciliation Types

1.  **QoS Billing vs. Chargeback**: Compares `CommercialQoSBillingRecord` with the original `CommercialQueueChargeback`.
2.  **Wallet vs. QoS Billing**: Compares `AiWalletTransaction` with the billing record that triggered it.
3.  **Invoice vs. QoS Billing**: Compares `BillingInvoice` totals with the sum of associated QoS billing records.

### Statuses

-   **MATCHED**: Amounts match perfectly or within the threshold.
-   **WARNING**: Discrepancy detected but within a minor threshold.
-   **MISMATCH**: Significant discrepancy detected (creates an audit event).
-   **INVESTIGATING**: Admin is reviewing the discrepancy.
-   **RESOLVED**: Discrepancy explained or corrected manually.

### Configuration

-   `COMMERCIAL_FINANCIAL_RECONCILIATION_ENABLED`: Enable/disable the reconciliation system.
-   `COMMERCIAL_FINANCIAL_RECONCILIATION_THRESHOLD_PERCENT`: The percentage delta allowed before marking as a mismatch (default 2%).

## Dispute Management

Dispute management allows clients to contest specific charges or wallet debits through the Customer Portal.

### Process Flow

1.  **Open**: Client submits a dispute via the portal, referencing a specific billing record, invoice, or wallet transaction.
2.  **Under Review**: Admin acknowledges the dispute and begins investigation.
3.  **Resolved/Rejected**: Admin provides a resolution.
4.  **Credited**: If the dispute is resolved in favor of the client, a manual credit is issued to their wallet.

### Configuration

-   `COMMERCIAL_FINANCIAL_DISPUTE_ENABLED`: Enable/disable the dispute management system.
-   `COMMERCIAL_FINANCIAL_MANUAL_CREDIT_ENABLED`: Enable/disable the ability for admins to issue manual credits (default false).

## Immutable Audit Trail

Every significant financial event is recorded in an immutable audit trail.

### Hashing Mechanism

Each `CommercialFinancialAuditEvent` includes an `immutable_hash`. This hash is calculated using:
`SHA256(previous_hash + event_type + amount + timestamp)`

This creates a hash chain where tampering with any record breaks the chain for all subsequent records.

### Validation

Admins can run a chain validation to ensure the integrity of the financial history:
`GET /admin/billing/audit/validate-chain`

## Administration

### Endpoints

-   `GET /admin/billing/reconciliation/overview`: Summary of all reconciliation tasks.
-   `POST /admin/billing/reconciliation/run`: Manually trigger a reconciliation run.
-   `GET /admin/billing/reconciliation/mismatches`: List all detected discrepancies.
-   `GET /admin/billing/disputes`: List and filter disputes.
-   `POST /admin/billing/disputes/{id}/resolve`: Resolve a dispute with optional credit.

## Troubleshooting

### Mismatch Detected

If a mismatch is detected:
1.  Check the `notes` field in the reconciliation record for details.
2.  Verify the original logs for the related `chargeback_id`.
3.  Ensure no manual database edits were made to billing records or wallet transactions.

### Audit Chain Invalid

If `validate-chain` returns `is_valid: false`:
1.  Identify the first record where the hash doesn't match.
2.  This indicates data tampering or a system error during hash calculation.
3.  Restore from a known good backup if necessary.
