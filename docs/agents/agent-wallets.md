# Agent Wallets

## Overview
Agent Wallets provide a governed financial layer for AI agents, allowing them to manage autonomous budgets, track expenses, and (optionally) interact with external payment systems like Stripe or Web3.

## Core Components
- **Internal Ledger**: A persistent, immutable record of every credit and debit transaction performed by an agent.
- **Budget Control**: Strict limits on spend per run, daily quotas, and maximum balances.
- **Spend Authorization**: A mandatory gate that checks if a requested expense is within limits or requires manual human approval.

## Financial Safety
1. **Internal by Default**: All wallets start as `internal` providers. No real-world funds are moved unless explicitly configured.
2. **External Spend Gate**: Real-world spending is globally controlled by the `AGENT_WALLET_EXTERNAL_SPEND_ENABLED` flag.
3. **Approval Thresholds**: Any transaction exceeding the agent's `approval_threshold` is paused until an administrator provides a digital signature/approval.
4. **Auditability**: Every transaction is linked to an `agent_run` ID and a unique `transaction_hash`.

## Configuration
- `AGENT_WALLETS_ENABLED`: Globally enables the wallet subsystem.
- `AGENT_WALLET_STRIPE_ENABLED`: Enables the opt-in Stripe Connect provider.
- `AGENT_WALLET_WEB3_ENABLED`: Enables the opt-in Web3/Crypto provider.
