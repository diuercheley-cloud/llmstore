# Commercial QoS Billing & Financial Integration

Phase 26 introduces the integration of QoS Priority Queue usage with the billing and wallet systems. This allows for automated or manual financial reconciliation based on the operational costs of providing priority access.

## Billing Modes

The system supports four billing modes, controlled by `COMMERCIAL_QOS_BILLING_MODE`:

1.  **`disabled`**: No billing records are generated.
2.  **`report_only` (Default)**: Billing records are calculated and stored for observability but no real financial action (invoice or wallet debit) is taken.
3.  **`invoice_line_item`**: Billing records can be attached to existing invoices as additional line items.
4.  **`wallet_debit_opt_in`**: Allows for automatic or manual debit from the client's AI Wallet, provided `COMMERCIAL_QOS_BILLING_DEBIT_WALLET=true` and the client has opted in.

## Calculation Logic

The billable amount is derived from the **Chargeback** data generated in Phase 25.

### Billable Amount Formula:
`Billable Amount = Internal Cost + (Optional) Opportunity Cost`

- **Internal Cost**: Estimated cost of compute resources used while in priority.
- **Opportunity Cost**: Estimated cost of delaying lower-tier requests (disabled by default).

### Configuration:
- `COMMERCIAL_QOS_BILLING_INCLUDE_OPPORTUNITY_COST`: If `true`, includes opportunity cost in the billable amount.
- `COMMERCIAL_QOS_BILLING_MIN_AMOUNT_BRL`: Minimum amount required to generate a billable record (default: 0.01 BRL).

## Safety & Limits

To prevent unexpected costs, several safety mechanisms are in place:

- **Daily Debit Limit**: `COMMERCIAL_QOS_BILLING_MAX_DAILY_DEBIT_BRL_PER_CLIENT` (default: 100.00 BRL).
- **Idempotency**: Records are generated once per client/period/tier/model combination.
- **Opt-in Requirement**: Wallet debits require explicit configuration and mode selection.

## Client Portal

Clients can view their QoS usage and billing history in the **Account > QoS Usage** section of the portal. This view includes:
- Period of usage.
- QoS Tier used.
- Priority slots consumed.
- Calculated billable amount.
- Status (Calculated, Invoiced, Debited).

## Admin Operations

Administrators can manage QoS billing through the **Admin Dashboard > Billing > QoS**:
- **Generate Records**: Manually trigger calculation for a specific lookback period.
- **Attach to Invoice**: Associate a record with a pending invoice.
- **Debit Wallet**: Manually trigger a wallet debit for a record.
- **Export Data**: Download billing history in JSON or CSV.

## Risks & Limitations

- **Statelessness**: Billing is calculated based on historical chargeback logs. If logs are lost before processing, data may be incomplete.
- **Invoice Flatness**: In the current version, `BillingInvoice` does not support multiple line items natively. Attaching a QoS record updates the total amount and creates an association, but detailed breakdown may only be visible in the QoS Billing records.
- **Wallet Balance**: If a client has insufficient funds and automatic debit is enabled, the record status will be marked as `failed`.
