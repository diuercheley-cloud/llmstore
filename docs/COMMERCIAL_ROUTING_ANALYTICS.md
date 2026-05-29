---
owner: platform-ops
status: consolidated
---

# Commercial Routing Analytics

## Overview

The Commercial Routing Analytics system provides persistence and reporting for routing decisions made by the LLM Inference Stack. It tracks which providers and models are selected, why they were chosen, and how their estimated financials compare to actual results.

## Key Features

- **Persistent Events**: Every routing decision is saved in the `commercial_routing_events` table.
- **Financial Tracking**: Tracks estimated cost, revenue, and margin at the time of routing.
- **Actuals Update**: When a request completes, the event is updated with actual tokens used, real cost, and real margin.
- **Sanitization**: Automatically removes sensitive information like API keys, prompts, and responses before saving.
- **Admin Dashboard**: Integrated view in the Admin UI showing today's summaries and recent events.
- **Best-Effort Design**: Analytics operations are designed not to break the main inference flow if they fail.

## Database Schema (`commercial_routing_events`)

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary Key |
| `created_at` | DateTime | Event timestamp |
| `client_id` | UUID | Associated client |
| `correlation_id`| String | Link to Request Log |
| `selected_provider`| String | Provider chosen for the request |
| `estimated_margin_brl` | Numeric | Predicted profit at routing time |
| `actual_margin_brl` | Numeric | Real profit after completion |
| `fallback_used` | Boolean | If local fallback was triggered |
| `blocked` | Boolean | If request was blocked by guardrails |
| `commercial_config_id` | UUID | ID of the dynamic config used (Phase 9) |
| `commercial_config_variant` | String | Variant used: `stable`, `canary`, or `default` (Phase 9) |
| `ranked_routes_json` | JSON | Sanitized list of all candidates considered |

## Endpoints

### GET `/admin/commercial-routing/analytics/summary`
Returns a summary of today's events, including total counts, fallbacks, blocks, and aggregated financials.

### GET `/admin/commercial-routing/events`
Lists recent routing events with filters for `client_id`, `provider`, `blocked`, and `fallback_used`.

## Technical Implementation

### Service
Located at `app/services/routing/commercial_analytics.py`. Handles recording, updating, and summarizing events.

### Integration
- **`app/api/client.py`**: Calls `record_routing_event` during route selection and `update_actual_financials` after the request finishes.
- **`app/services/routing/smart_router.py`**: Captures detailed ranking data during the `commercial_profit` strategy execution.

## Validation

Run the following command to validate the implementation:
```bash
make validate-commercial-routing-analytics
```

Or run the tests:
```bash
pytest tests/test_commercial_routing_analytics.py
```
