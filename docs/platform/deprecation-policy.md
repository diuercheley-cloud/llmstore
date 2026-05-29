---
owner: platform-ops
status: consolidated
---

# API Deprecation & Sunset Policy

To minimize operational complexity, the platform regularly consolidates redundant endpoints and retires legacy APIs. This policy defines the deprecation headers, notification periods, and transition rules.

## Deprecation Headers

Any API endpoint marked as `deprecated` in [api-surface.yaml](file:///home/kleber/llm-inference-stack/config/api-surface.yaml) will automatically return the following response headers to notify clients:

- `X-Deprecated-Endpoint`: Always set to `true`.
- `X-Sunset-Date`: The scheduled sunset date (formatted as `YYYY-MM-DD`). Defaults to `2026-12-31`.
- `Sunset`: The scheduled sunset date (formatted as `YYYY-MM-DD`). Defaults to `2026-12-31`.
- `X-Replacement-Endpoint`: (Optional) The path of the replacement API.

## Sunset Process

1. **Identification**: Identify redundant or legacy endpoints.
2. **Transition Status**: Mark the endpoint status as `deprecated` in `config/api-surface.yaml` and set a `sunset_date`.
3. **Migration Window**: The deprecation headers will be active for a minimum transition period (typically 30 days) to allow clients to update integrations.
4. **Retirement**: Once the sunset date is reached, the endpoint is deleted or returns a `410 Gone` error.
