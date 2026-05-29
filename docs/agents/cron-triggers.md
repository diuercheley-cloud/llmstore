---
owner: platform-ops
status: consolidated
---

# Cron Triggers and Timezone Support

Cron triggers schedule recurrent agent runs based on cron expressions.

## Database Models

When creating a trigger with type `on_schedule`, the system automatically populates the `agent_scheduled_triggers` table:
- `cron_expression`: Standard 5-field cron format.
- `timezone`: Timezone name (e.g. `America/Sao_Paulo`, `UTC`, `Asia/Tokyo`).
- `next_run_at`: Next UTC execution time computed automatically on schedule creation and after each firing.

## Timezone Calculations

Cron expressions are parsed and evaluated using `zoneinfo` timezones:
1. The scheduler fetches the current UTC time.
2. The UTC time is converted to the trigger's target local timezone.
3. The next occurrence of the cron expression is calculated in that local timezone.
4. The local execution datetime is converted back to UTC and saved to `next_run_at`.

This ensures daylight saving transitions and local timezone offsets are accurately respected (e.g., executing exactly at 09:00 AM local time daily).

## Example Config

```json
{
  "cron_expression": "0 9 * * 1-5",
  "timezone": "America/Sao_Paulo"
}
```
*Executes every weekday at 09:00 AM Sao Paulo time.*
