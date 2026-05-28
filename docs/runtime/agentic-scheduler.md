# Agentic Secure Scheduler

The Agentic Scheduler is responsible for triggering agent runs based on time (cron) or events, ensuring that these triggers are fired reliably and exactly once.

## Components

### Agent Scheduler (Cron)
The `AgentScheduler` monitors `AgentScheduledTrigger` records. It uses the same `SKIP LOCKED` strategy as the durable queue to ensure that in a multi-instance scheduler setup, only one instance fires a specific trigger at its scheduled time.

### Workflow Scheduler
For stateful workflows, the `WorkflowScheduler` manages timers and "ready" runs. It coordinates with the `WorkflowEngine` to wake up workflows that are sleeping or waiting for signals.

## Resilience

### Atomic Transitions
Firing a trigger involves:
1. Selecting the due trigger `FOR UPDATE SKIP LOCKED`.
2. Enqueueing the execution job.
3. Updating the `next_run_at` timestamp for the trigger.
4. Committing the transaction.

This atomicity ensures that if a scheduler instance crashes mid-process, the trigger remains "due" and will be picked up by another instance.

### Distributed Locking
For workflow execution, additional distributed locks are used at the run level to ensure that state transitions are serialized and consistent across the cluster.

## Monitoring
The scheduler's health can be monitored via heartbeats in the `agent_worker_heartbeats` table (which tracks all active execution plane components).
