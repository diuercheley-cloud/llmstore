# Adapter Promotion Workflow - Operational Guide

## Promotion Process
1.  **Initialize Workflow**: Create a new promotion workflow for a registered adapter.
2.  **Evaluate Gates**: The system automatically checks mandatory gates (registry status, sandbox results, etc.).
3.  **Staging Simulation**: For production targets, ensure a staging simulation has been recorded.
4.  **Promote**: Once all gates pass, transition the adapter to the next stage.
5.  **Verify**: Download the promotion receipt for audit purposes.

## Rollback Procedure
If a promoted adapter is found to be problematic:
1.  Identify the active promotion workflow.
2.  Issue a rollback command specifying the target stage (e.g., `sandboxed`).
3.  Provide a mandatory reason for the rollback.

## Monitoring
Operational metrics are available in the Admin Dashboard under the "Adapter Promotion Workflow" section:
- **Active Workflows**: Total workflows currently in progress.
- **Promoted**: Total adapters that reached their target stage.
- **Blocked**: Workflows stuck on failed gates.
- **Production Eligible**: Count of adapters ready for production (eligibility only).

## Important Safety Notes
- **Eligibility Only**: "Production Eligible" means the adapter has passed all governance gates. It does NOT mean the adapter is currently running or that production infra has been modified.
- **No Real PKI**: All "signatures" are placeholders for this phase.
- **Offline-First**: This workflow does not require internet access or external cloud services.
