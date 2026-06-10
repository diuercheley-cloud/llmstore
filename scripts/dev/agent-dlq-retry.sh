#!/usr/bin/env bash
# Owner: agent-platform
# Status: beta

echo "Re-enqueueing DLQ jobs..."
docker compose exec -T postgres psql -U postgres -d app -c "
UPDATE agent_execution_jobs
SET queue_status = 'queued', attempt_count = 0, available_at = NOW(), locked_by = NULL, locked_until = NULL
WHERE queue_status = 'dead_letter';
DELETE FROM agent_execution_dead_letters;
"
echo "Jobs re-enqueued."
