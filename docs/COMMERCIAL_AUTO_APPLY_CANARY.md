---
owner: platform-ops
status: consolidated
---

# Commercial Auto Apply Canary (Phase 8)

## Overview
Auto Apply Canary allows the system to automatically adjust routing costs (calibration) based on historical error data, using a safe canary deployment strategy. This ensures that the system stays calibrated with minimal manual intervention while strictly adhering to safety guardrails.

## Operational Modes
Managed by `COMMERCIAL_CALIBRATION_AUTO_APPLY_MODE`:
- `disabled`: Auto-apply is completely off.
- `dry_run` (Default): Evaluates eligibility and logs actions, but does not create new configurations.
- `canary`: Creates a new active configuration for a small percentage of traffic.

## Eligibility Criteria
A recommendation is only auto-applied if ALL criteria are met:
1. `COMMERCIAL_CALIBRATION_AUTO_APPLY=true`.
2. Confidence is `high`.
3. Total sample count >= `COMMERCIAL_CALIBRATION_AUTO_APPLY_MIN_RECENT_SAMPLES` (Default: 20).
4. Recommended cost change <= `COMMERCIAL_CALIBRATION_AUTO_APPLY_MAX_CHANGE_PERCENT` (Default: 10%).
5. Rate limit: No more than 1 auto-apply per provider/model per hour (Default).

## Deterministic Hashing (Canary Selection)
The system uses MD5 hashing of `request_id`, `correlation_id`, or `client_id` to assign each request to a bucket (0-99).
If the bucket index is lower than `canary_percent` (Default: 5%), the canary configuration is used.
This ensures:
- **Consistency**: The same request (or same client) always gets the same configuration.
- **Gradual Rollout**: We can safely test changes on 5% of traffic before promoting to 100%.

## Administrative Actions
- **Promote**: Transforms a canary config into a 100% stable config, deactivating the previous stable config.
- **Rollback**: Immediately deactivates the canary config, reverting all traffic to the stable config.

## Auditing
All actions are logged in `AdminActionLog`:
- `auto_apply_dry_run`
- `auto_apply_canary_created`
- `auto_apply_canary_promoted`
- `auto_apply_canary_rollback`
- `auto_apply_rejected` (with reasons)

## Canary Promotion
Since Phase 9, canary configurations can be automatically promoted to stable based on SLOs. 
See [COMMERCIAL_CANARY_PROMOTION.md](COMMERCIAL_CANARY_PROMOTION.md) for details.

## Troubleshooting
- If auto-apply is not running, check confidence levels and sample counts in the Calibration Report.
- Use `POST /admin/routing/commercial-configs/auto-apply/dry-run` to see why recommendations are being rejected.
- Check logs for "auto_apply_rejected" entries.

## Risks & Guardrails
- **Max Change**: Automatic changes are capped at 10% to prevent massive routing shifts.
- **High Confidence Only**: Only data with low variance and sufficient samples is used.
- **Canary Isolation**: If a canary performs poorly, it only affects a small fraction of requests and can be rolled back instantly.
