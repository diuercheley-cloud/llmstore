---
owner: platform-ops
status: consolidated
---

# Commercial QoS / SLA-Aware Routing

This document describes Phase 20: Adaptive SLA-Aware Routing with QoS Tiers.

## Overview

Adaptive SLA-Aware Routing allows the system to route requests based on the client's service level agreement (SLA) and Quality of Service (QoS) tier. This ensures that high-value clients (Enterprise, Premium) receive better performance and reliability while lower tiers (Free, Basic) are routed through more cost-effective paths.

## QoS Tiers

The system defines 5 default tiers:

| Tier | Cloud Allowed | Latency Target | Priority | Description |
|------|---------------|----------------|----------|-------------|
| **Free** | No | 1500ms | 0 | Lowest priority, local-only. |
| **Basic** | No | 800ms | 10 | Local-first, fallback allowed. |
| **Pro** | Yes (Margin > 5%) | 400ms | 50 | Cloud allowed if profitable. |
| **Premium** | Yes | 250ms | 100 | Low latency, cross-cluster allowed. |
| **Enterprise** | Yes | 150ms | 1000 | Maximum priority, strictest SLA. |

## SLA Constraints

Each tier has several constraints enforced during routing:
- `target_latency_ms`: Ideal latency for the request.
- `max_p95_latency_ms`: Maximum allowed p95 latency before considering the SLA violated.
- `min_margin_percent`: Minimum profit margin required to use a route.
- `max_cost_per_request_brl`: Maximum cost allowed for a single request.
- `allow_cloud`: Whether cloud providers can be used.
- `allow_cross_cluster`: Whether requests can be forwarded to other clusters.
- `allow_degraded_cluster`: Whether degraded clusters are eligible for routing.
- `quality_floor`: Minimum model quality required.

## Degradation Policies

If no route satisfies the primary SLA constraints, the system applies a degradation policy:
- `block`: Reject the request.
- `fallback_local`: Attempt to use a local provider even if it doesn't meet SLA.
- `cheapest`: Use the cheapest available route regardless of SLA.
- `best_effort`: Use the best available route even if it violates some constraints.

## Queue Priority

For asynchronous jobs, the QoS tier determines the processing priority:
`Enterprise (1000) > Premium (200) > Pro (100) > Basic (50) > Free (10)`

## Admin API

- `GET /admin/routing/qos/tiers`: List all tiers.
- `POST /admin/routing/qos/tiers`: Create a new tier.
- `PATCH /admin/routing/qos/tiers/{id}`: Update a tier.
- `GET /admin/routing/qos/overview`: Get a summary of QoS status.
- `POST /admin/routing/qos/simulate`: Simulate routing for a specific plan/tier.

## Simulation Example

```json
POST /admin/routing/qos/simulate
{
  "plan": "premium",
  "model": "gpt-4",
  "estimated_tokens": 2000
}
```

Response:
```json
{
  "tier": "Premium",
  "selected_route": { ... },
  "sla_pass": true,
  "degradation_path": null
}
```

## Monitoring

The Executive Dashboard now includes a "QoS / SLA Routing" section showing:
- SLA pass rate per tier.
- Average latency per tier.
- Requests distribution by tier.
