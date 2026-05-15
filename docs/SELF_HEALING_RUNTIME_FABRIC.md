# Phase 65: Self-Healing Deterministic Runtime Fabric

## Overview

The Self-Healing Deterministic Runtime Fabric is an autonomous operational mesh designed to ensure the continuous and correct operation of the LLM Inference Stack. It detects failures, degradations, and determinism drifts, and automatically initiates remediation actions within the bounds of defined governance policies.

## Core Components

### 1. Runtime Fabric Service
Responsible for monitoring node health and detecting initial failure events.
- **Heartbeat Monitoring:** Continuous status reporting from all nodes.
- **Event Detection:** Automatic triggering of fabric events on failure or degradation.

### 2. Runtime Recovery Service
Orchestrates recovery plans based on detected events.
- **Recovery Modes:**
    - `advisory`: Log-only mode.
    - `dry_run`: Simulates recovery actions.
    - `guarded_recovery`: Execution with manual or automated approval gates.
    - `sovereign_safe_mode`: Priority on local stability and airgap compliance.

### 3. Runtime Healing Service
Executes specific remediation actions.
- **Action Types:** `restart_service`, `rollback_state`, `replay_workflow`, `isolate_node`, `resync_mesh`.
- **Signed Receipts:** Every action generates a signed receipt for auditability and immutability.

### 4. Determinism Repair Service
Specialized in maintaining execution consistency.
- **Drift Detection:** Identifies deviations in deterministic workflow hashes.
- **Replay Repair:** Automatically re-executes workflow steps to restore state consistency.

## Security & Governance

- **Blast Radius Enforcement:** Healing actions are restricted to the affected components and nodes.
- **Immutable Audit Trail:** All events, plans, and actions are logged in immutable database tables.
- **Governance Approval Gates:** Critical recovery plans require approval from the Governance Supervisor or an authorized administrator.
- **Replay-Safe Recovery:** Ensures that replaying workflows does not cause side effects or duplicate billing.

## API Reference

### Admin Endpoints
- `GET /admin/runtime/fabric`: Get current fabric health status.
- `POST /admin/runtime/fabric/heartbeat`: Report node health.
- `GET /admin/runtime/healing`: List recent healing events.
- `POST /admin/runtime/recovery`: Create a new recovery plan.
- `POST /admin/runtime/recovery/{plan_id}/execute`: Execute a recovery plan.
- `GET /admin/runtime/drift`: List active determinism drifts.
- `POST /admin/runtime/replay-repair/{drift_id}`: Trigger automated repair for a drift.

### Portal Endpoints
- `GET /portal/runtime/status`: Public-facing runtime health status.

## Usage Guide

### Enabling Self-Healing
The fabric is enabled by default in commercial deployments. Configuration can be adjusted in `routing-policies.json`.

### Monitoring Drift
Administrators should monitor the `/admin/runtime/drift` endpoint to identify workflows that have diverged from their deterministic path.

### Manual Intervention
While the fabric is autonomous, administrators can manually create and execute recovery plans for complex failure scenarios that fall outside automated routines.
