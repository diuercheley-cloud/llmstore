---
owner: platform-ops
status: consolidated
---

# QoS Fairness Observability & Queue Chargeback

## Overview

Phase 25 introduces advanced observability for the QoS Priority Queue and an operational chargeback mechanism. These tools allow administrators to measure how "fair" the queueing system is and estimate the operational costs associated with different QoS tiers and clients.

## Fairness Observability

### Metrics

1.  **Jain's Fairness Index**: A measure of how equally resources (wait times adjusted by priority) are distributed among tiers.
    *   `1.0`: Perfectly fair (each tier gets wait times proportional to its priority).
    *   `< 1.0`: Some tiers are being underserved or overserved.
2.  **Starvation**: Detects jobs waiting longer than `COMMERCIAL_QOS_STARVATION_THRESHOLD_SECONDS` (default 30 minutes).
3.  **Priority Inversion**: Cases where a lower-priority job was processed while a higher-priority job was already waiting.
4.  **SLA Queue Violations**: Counts how many jobs exceeded their tier's `target_latency_ms` while in queue.

### How to Monitor
Access the **Admin Dashboard** > **QoS & Filas** tab.
You can also use the CLI:
```bash
make validate-commercial-qos-fairness
```

## Queue Chargeback

The chargeback system estimates the internal operational cost of serving requests through the priority queue. It does **not** affect real billing yet, but serves as a basis for financial optimization.

### Cost Model

1.  **Compute Seconds**: The actual time the job spent occupying a worker slot.
2.  **Priority Slots**: Compute seconds weighted by the job's priority.
    *   Base priority (100) = 1.0x multiplier.
    *   Enterprise priority (500) = 5.0x multiplier.
3.  **Opportunity Cost**: Estimated cost of blocking high-priority jobs.
    *   Calculated when a low-priority job (Free/Basic) is running while high-priority jobs (Premium/Enterprise) are waiting in queue.
4.  **Chargeback Amount**: `(Priority Slots * Cost per Second) + Opportunity Cost`.

### Configuration

*   `COMMERCIAL_QOS_CHARGEBACK_ENABLED`: Enable/disable tracking.
*   `COMMERCIAL_QOS_PRIORITY_SLOT_COST_BRL_PER_SECOND`: Base cost for a priority 100 slot (default R$ 0.001).
*   `COMMERCIAL_QOS_STARVATION_THRESHOLD_SECONDS`: Threshold for starvation alerts.

## Exporting Reports

Chargeback reports can be exported in JSON or CSV format for integration with external BI tools:
`GET /admin/routing/qos/chargeback/export?format=csv&hours=24`

## Optimization Strategy

*   **Low Fairness Index**: Consider increasing the `COMMERCIAL_QOS_QUEUE_AGING_SECONDS` to give more priority to old low-tier jobs.
*   **High Opportunity Cost**: Indicates that low-tier traffic is significantly impacting premium users. Consider increasing price for low tiers or adding more worker capacity.
*   **High Starvation**: Suggests the system is over-capacity. Review `MAX_CONCURRENT_GENERATIONS`.
