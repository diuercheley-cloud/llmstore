---
owner: platform-ops
status: consolidated
---

# Agentic Durable Queue

The Agent Execution Plane uses a durable queue backed by Postgres to ensure that agent runs are executed reliably even in the face of worker crashes or system restarts.

## Key Features

### Durable Persistence
All execution jobs are stored in the `agent_execution_jobs` table. This ensures that even if the entire worker cluster goes down, the state of pending, running, and failed jobs is preserved.

### Safe Concurrency (SKIP LOCKED)
To prevent multiple workers from picking up the same job, the system uses Postgres row-level locking with the `SKIP LOCKED` clause:

```sql
SELECT * FROM agent_execution_jobs
WHERE queue_status = 'queued' AND available_at <= NOW()
ORDER BY priority DESC, available_at ASC
LIMIT 1
FOR UPDATE SKIP LOCKED;
```

This allows high-throughput concurrent job processing without contention or double-execution.

### Lease Management
When a worker picks up a job, it "leases" it by setting `locked_by` and `locked_until`. The worker is responsible for renewing this lease via a heartbeat loop. If a worker crashes, its lease will eventually expire, and a recovery job will return the job to the `queued` status for another worker to pick up.

### Idempotency and Deduplication
- **Idempotency Key:** Ensures that a specific request to enqueue a job (e.g., from a client) is processed exactly once.
- **Deduplication Key:** Prevents multiple active jobs for the same event or resource. If a job with the same deduplication key is already in an active state (`queued`, `leased`, `running`), new enqueue attempts will return the existing job instead of creating a new one.

### Dead Letter Queue (DLQ)
Jobs that exceed their `max_attempts` (either through explicit failure or repeated lease expirations) are moved to the `dead_letter` status and a record is created in `agent_execution_dead_letters` with the `dlq_reason`. This prevents "poison pill" jobs from infinitely cycling through the queue.

## Schema Highlights

| Column | Description |
|--------|-------------|
| `queue_status` | Current state (queued, leased, running, etc.) |
| `priority` | Higher numbers are processed first |
| `available_at` | When the job is eligible for pickup (handles delayed retries) |
| `locked_by` | Worker ID holding the current lease |
| `locked_until` | Expiration timestamp of the current lease |
| `attempt_count` | Number of execution attempts made |
| `max_attempts` | Maximum allowed attempts before DLQ |
| `idempotency_key` | Unique key for request idempotency |
| `deduplication_key` | Key to prevent concurrent duplicate jobs |
