---
owner: platform-ops
status: consolidated
---

# Operations Correlation Engine (Phase 70)

## Architecture Overview

The **Operations Correlation Engine** is a deterministic, advisory-only system designed to identify patterns across multiple infrastructure domains. It operates within the control plane, aggregating events and forecasts to detect cross-domain impacts and establish trust links between system components.

### Core Principles
- **Deterministic:** Given the same set of inputs, the engine always produces the same output.
- **Advisory-Only:** No automatic enforcement or remediation is performed. All findings are for informational and auditing purposes.
- **Offline-First:** Compatible with air-gapped deployments; no external cloud connection or SaaS dependency.
- **Immutable:** Every correlation and trust link is hashed and verifiable via cryptographic receipts.

## Correlation Engine

The engine uses a rule-based deterministic logic to correlate events. It analyzes:
- **Temporal proximity:** Events occurring within a close time window.
- **Domain intersection:** Overlapping impacts between compute, storage, network, and IAM.
- **Severity escalation:** Patterns indicating a cascading failure or risk trend.

### Implementation
Located at: `app/services/operations/correlation/deterministic_correlation_engine.py`

## Trust Graph

The **Operational Trust Graph** maps the relationships and trust scores between different nodes in the system.
- **Nodes:** System domains (e.g., `billing`, `runtime`, `compute`).
- **Edges:** Trust links established via successful correlations or historical stability.
- **Trust Score:** A normalized value (0.0 to 1.0) representing the reliability of a link.

### Implementation
Located at: `app/services/operations/correlation/trust_graph.py`

## Receipts

Every correlation event generates a **Cryptographic Receipt**. This receipt includes:
- **Correlation ID:** Unique identifier.
- **Input Hash:** Deterministic hash of the input events.
- **Output Hash:** Hash of the engine's result.
- **Immutable Proof:** A SHA-256 chain ensuring the correlation cannot be tampered with after generation.

### Implementation
Located at: `app/services/operations/correlation/receipts.py`

## Audit Events

All engine activities are logged as immutable audit events, ensuring a transparent history of operational insights.
- `CORRELATION_CREATED`
- `TRUST_LINK_ESTABLISHED`
- `GRAPH_REBUILT`

### Implementation
Located at: `app/services/operations/correlation/audit_events.py`

## APIs

### Admin API
- `POST /admin/operations/correlations/run`: Manually trigger a correlation cycle.
- `GET /admin/operations/correlations/`: List recent correlations.
- `POST /admin/operations/correlations/trust-graph/build`: Rebuild the trust graph.
- `GET /admin/operations/correlations/trust-graph`: View current graph summary.

### Portal API
- `GET /portal/operations/correlations/`: View client-specific correlations.
- `GET /portal/operations/correlations/trust-graph`: View client-specific trust score summary.

## Dashboard

The engine is integrated into both the **Admin Dashboard** and the **Client Portal**.
- **Admin View:** Full visibility into cross-domain patterns, trust scores, and receipt verification.
- **Portal View:** High-level overview of operational health and trust links for the client's environment.

## Limitations
- **Advisory Only:** Cannot block or modify system behavior.
- **Static Rules:** Rules are deterministic and do not "learn" from non-deterministic ML models.
- **Domain Scope:** Currently limited to registered infrastructure domains.

## Offline Compatibility
The engine requires **zero** external network access. It uses local database persistence and deterministic hashing, making it ideal for sovereign and air-gapped environments.

## Security Notes
- **Tenant Isolation:** Correlations are strictly isolated per `client_id`.
- **No Payload Leakage:** Receipts and summaries do not include sensitive event payloads, only hashes and metadata.
- **Read-Only Enforcement:** The engine has no write-access to core runtime enforcement layers.
