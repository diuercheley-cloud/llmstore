<!-- synced_from: docs/security/agent-spend-controls.md -->

> Source of truth: `docs/security/agent-spend-controls.md`

# Agent Spend Controls

## Governance Model
The platform implements a "Deny-by-Default" posture for autonomous agent spending.

### 1. Authorization Workflow
When an agent requests a payment:
- The system identifies the wallet and its associated `AgentWalletLimit` record.
- If `amount > max_per_run`, the request is immediately **blocked**.
- If `amount >= approval_threshold`, a `SpendAuthorization` event is created with status `pending`, and the agent execution is paused.
- Once an operator approves, the status shifts to `approved`, and the transaction proceeds.

### 2. Provider Isolation
- **Internal Provider**: Credits/Debits exist only within the platform's database. No external API calls are made.
- **External Providers (Stripe/Web3)**: Require explicit tenant-level onboarding and global feature flag activation. Even when enabled, they respect all internal budget limits.

### 3. Immutable Ledgering
The `agent_wallet_ledger_entries` table acts as the source of truth. Each entry contains a `transaction_hash` covering the critical transaction data, ensuring that historical records cannot be altered without detection.

### 4. Tenant Boundaries
Wallets are strictly isolated by `tenant_id`. An agent belonging to Tenant A cannot access or spend from a wallet belonging to Tenant B.
