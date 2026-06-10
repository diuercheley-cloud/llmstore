#!/usr/bin/env bash
# Owner: agent-platform
# Status: beta

echo "=== Agent Queue Status ==="
docker compose exec -T postgres psql -U postgres -d app -c "
SELECT queue_status, count(*) FROM agent_execution_jobs GROUP BY queue_status;
SELECT worker_id, status, last_heartbeat FROM agent_worker_heartbeats;
SELECT count(*) as dead_letters FROM agent_execution_dead_letters;
"
