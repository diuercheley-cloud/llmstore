# Manual Commercial Configuration Application

This document describes the system for manually applying commercial routing configurations, such as cost multipliers and weights, typically following calibration recommendations.

## Overview

Phase 7 introduces the ability for administrators to override default commercial routing settings through a scoped configuration system. This allows for fine-tuning the `commercial_profit` routing strategy based on real-world performance and cost data.

## Configuration Model

The `CommercialRoutingConfig` model persists the following settings:

- **Cost Multiplier**: Adjusts the estimated provider cost.
- **Weights**: `margin_weight`, `latency_weight`, `quality_weight` (must sum to 1.0).
- **Local Route Bonus**: Fixed score bonus for local providers.
- **Min Margin Percent**: Minimum profit margin required for cloud routes.

## Specificity Precedence

When multiple active configurations exist, the most specific one wins:

1. `provider_model`: Exact provider and model match.
2. `model`: Exact model match across all providers.
3. `provider`: Exact provider match across all models.
4. `global`: Applies to all routes.
5. `env default`: Fallback to environment variables.

## Admin API

### List Configurations
`GET /admin/routing/commercial-configs?active_only=true`

### Apply Recommendation
`POST /admin/routing/commercial-configs/apply-recommendation`
```json
{
  "provider": "openai",
  "model": "gpt-4",
  "recommended_cost_multiplier": 1.15,
  "confidence": "high",
  "notes": "applied after 7-day calibration",
  "force": false
}
```

### Deactivate Configuration
`POST /admin/routing/commercial-configs/{config_id}/deactivate`

### Rollback
`POST /admin/routing/commercial-configs/rollback`
```json
{
  "scope_type": "provider_model",
  "provider": "openai",
  "model": "gpt-4"
}
```

### Auto-Apply (Phase 8)
Automated application of recommendations via canary. See [COMMERCIAL_AUTO_APPLY_CANARY.md](COMMERCIAL_AUTO_APPLY_CANARY.md).

## Dashboard UI

The admin dashboard at `/static/admin/` includes a **Commercial Configs** section with:
- **Apply recommendation**: Opens a form dialog to configure provider, model, cost multiplier, confidence, notes, and force flag.
- **Config list**: Shows all active (and optionally inactive) configs with scope, multiplier, weights, source, and active status.
- **Deactivate**: Each active config row has a deactivate button.
- **Rollback**: Collapsible section at the bottom allows rolling back to a previous config by scope.
- **Confirmation dialogs**:
  - Warnings for cost multipliers >25% change, medium confidence, or force=true.
  - Low confidence recommendations blocked unless force=true is checked.
  - Visual confirmation required before applying.

## Rollback Mechanism

Rollback works by:
1. Deactivating the current active config for the given scope.
2. Reactivating the most recently created inactive config for the same scope.
3. Recording the action in `AdminActionLog` with before/after details.
4. If no previous config exists, the endpoint returns a 404 error and the current config remains active.

## Safety Limits

- **Cost Multiplier**: Restricted to `[0.3, 3.0]` unless `force=true` is used.
- **Weights**: Must sum exactly to `1.0`.
- **Confidence**: Low confidence recommendations cannot be applied without `force=true`.

## Auditing

All changes are recorded in the `AdminActionLog` with details of the previous and new settings, the actor who performed the change, and the reason.

## Troubleshooting

If the database is unavailable, the system automatically falls back to environment-based defaults without breaking user requests.
