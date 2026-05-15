# Commercial QoS: Priority Queue & Rate Limiting (Phase 24)

This phase implements a Redis Sorted Set-based priority queue for asynchronous jobs and advanced rate limiting per QoS tier.

## 1. QoS Priority Queue

The priority queue uses a Redis Sorted Set (`generation_jobs:priority`) to order jobs.

### Score Calculation
The score determines the processing order. A lower score means higher priority.

`score = -(priority_weight * 1,000,000) + created_at_ms + aging_adjustment`

- **priority_weight**: Defined per QoS tier (Enterprise=500, Premium=400, Pro=300, Basic=200, Free=100).
- **created_at_ms**: Ensures FIFO (First-In-First-Out) behavior within the same priority level.
- **aging_adjustment**: Reduces the score over time to prevent starvation of lower-priority jobs.

### Starvation Prevention (Aging)
A Lua script runs periodically (controlled by the worker or a scheduler) to subtract an `aging_step` (default: 100,000) from all jobs in the queue every `COMMERCIAL_QOS_QUEUE_AGING_SECONDS`.

After 10 aging intervals, a job effectively climbs one full priority level.

### Operation Modes
Controlled by `COMMERCIAL_QOS_PRIORITY_QUEUE_MODE`:
- `disabled`: Only uses the legacy list-based queue.
- `shadow`: Enqueues to both legacy and priority queues. Worker still consumes from legacy. Used for metric comparison.
- `active`: Worker consumes from the Redis Sorted Set.

## 2. QoS Rate Limiting

Tier-based rate limiting (RPM) enforced during job creation.

### Tiers and Limits
- **Free**: 10 RPM
- **Basic**: 60 RPM
- **Pro**: 300 RPM
- **Premium**: 1000 RPM
- **Enterprise**: 5000 RPM

### Modes
Controlled by `COMMERCIAL_QOS_RATE_LIMIT_MODE`:
- `report_only`: Requests above the limit are allowed but tagged as `throttled`.
- `enforce`: Requests above the limit are rejected with HTTP 429.

## 3. Configuration

```env
COMMERCIAL_QOS_PRIORITY_QUEUE_ENABLED=true
COMMERCIAL_QOS_PRIORITY_QUEUE_MODE=shadow
COMMERCIAL_QOS_QUEUE_AGING_SECONDS=300

COMMERCIAL_QOS_RATE_LIMITING_ENABLED=true
COMMERCIAL_QOS_RATE_LIMIT_MODE=report_only
```

## 4. Monitoring

Admin endpoints available at:
- `GET /admin/routing/qos/queue/overview`: Queue depth and status.
- `GET /admin/routing/qos/queue/jobs`: List prioritized jobs.
- `GET /admin/routing/qos/rate-limits/overview`: Limits per tier.
- `POST /admin/routing/qos/rate-limits/simulate`: Test rate limit for a client.
