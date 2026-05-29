---
owner: platform-ops
status: consolidated
---

# Commercial Global Routing (Dry-Run) - Phase 16

This document describes the Global Traffic Routing implementation in dry-run mode.

## Architecture

The Global Router uses data from the Federation layer to calculate routing recommendations between multiple clusters. In this phase, it operates as a **simulator and recommender**, never moving real traffic or altering the OpenAI-compatible flow.

## Scoring System

Clusters are scored on a 0-100 scale based on weighted factors:

1.  **Margin (40%)**: Calculated from `actual_margin_brl` and `actual_revenue_brl`. Negative margin results in a score of 0.
2.  **Latency (25%)**: Based on `avg_latency_ms`. Scores decrease as latency approaches `COMMERCIAL_GLOBAL_ROUTING_MAX_LATENCY_MS`.
3.  **Health (15%)**: `active` clusters get 100 points, `degraded` get 50, others get 0.
4.  **Region Preference (10%)**: Matches against `region_preference`. If `ALLOW_CROSS_REGION` is false, mismatch rejects the cluster.
5.  **Priority (10%)**: Normalized from the cluster registry priority (lower is better).

## Configuration

```bash
COMMERCIAL_GLOBAL_ROUTING_ENABLED=true
COMMERCIAL_GLOBAL_ROUTING_MODE=dry_run

COMMERCIAL_GLOBAL_ROUTING_MARGIN_WEIGHT=0.40
COMMERCIAL_GLOBAL_ROUTING_LATENCY_WEIGHT=0.25
COMMERCIAL_GLOBAL_ROUTING_HEALTH_WEIGHT=0.15
COMMERCIAL_GLOBAL_ROUTING_REGION_WEIGHT=0.10
COMMERCIAL_GLOBAL_ROUTING_PRIORITY_WEIGHT=0.10

COMMERCIAL_GLOBAL_ROUTING_REQUIRE_HEALTHY_CLUSTER=true
COMMERCIAL_GLOBAL_ROUTING_ALLOW_CROSS_REGION=false
COMMERCIAL_GLOBAL_ROUTING_MAX_LATENCY_MS=5000
```

## Constraints

- **Tenant Scope**: Respects `tenant_scope_json`. If a tenant is not in scope for a cluster, that cluster is rejected.
- **Region**: If `ALLOW_CROSS_REGION` is false, clusters in different regions are rejected if a preference is provided.
- **Health**: Clusters marked as `offline` or `disabled` are rejected if `REQUIRE_HEALTHY_CLUSTER` is true.

## Admin Endpoints

- `GET /admin/routing/global-router/overview`: General status and ranked clusters.
- `GET /admin/routing/global-router/recommendations`: Best recommendations based on current global state.
- `POST /admin/routing/global-router/simulate`: Simulate a specific request to see which cluster would be chosen.
- `GET /admin/routing/global-router/export?format=json|csv|html`: Export routing data.

## Simulation Payload

```json
{
  "tenant_id": "tenant-a",
  "provider": "openai",
  "model": "gpt-4",
  "region_preference": "us-east",
  "estimated_tokens": 2000
}
```

## Audit Logging

The following events are recorded in the audit log:
- `global_route_simulated`: When a simulation is performed.
- `cluster_rejected`: When a cluster is excluded from ranking.
- `cluster_recommended`: (Future) When a cluster is selected for real routing.

**Security Note**: Audit logs never contain prompts, responses, or API keys.
