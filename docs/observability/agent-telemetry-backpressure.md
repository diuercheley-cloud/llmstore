---
owner: platform-ops
status: consolidated
---

# Agent Telemetry Backpressure

## Overview

The telemetry backpressure system prevents span floods from overwhelming async exporters during agent execution peaks. It uses a bounded queue with priority-aware sampling and leaky-bucket rate limiting to ensure critical spans are never lost.

## Feature Flags

| Flag | Default | Description |
|------|---------|-------------|
| `AGENT_TELEMETRY_BACKPRESSURE_ENABLED` | `true` | Master toggle for telemetry backpressure |
| `AGENT_TELEMETRY_DROP_DEBUG_SPANS_ENABLED` | `true` | Allow dropping debug spans under pressure |
| `AGENT_TELEMETRY_STRICT_EXPORT` | `false` | Log warnings instead of blocking on export failure |

## Architecture

### Components

1. **Span Priority** — Classifies spans into four priority levels:
   - `critical`: errors, policy_denials, approvals, security (never dropped)
   - `high`: run start/end, tool calls
   - `normal`: model calls, memory calls (sampled at 50% under pressure)
   - `debug`: token-level/debug spans (first to be dropped)

2. **Leaky Bucket** — Per-tenant, per-agent, per-span-type, and per-exporter rate limiting:
   - Each dimension has independent capacity and leak rate
   - When a bucket overflows, the span is either queued or dropped based on priority

3. **Span Sampler** — Controls sampling rates per priority level:
   - Critical: 100% (always sampled)
   - High: 100%
   - Normal: 50%
   - Debug: 10%

4. **Telemetry Backpressure** — Main orchestrator with bounded queue:
   - When queue fills, debug spans are dropped first
   - Then normal spans are sampled
   - Critical spans are never dropped
   - Drop metrics are recorded

### Queue Behavior

```
enqueue(span)
  ├─ Backpressure disabled? → passthrough (no queue)
  ├─ Leaky bucket check
  │   ├─ Pass → queue span
  │   └─ Fail
  │       ├─ Critical span → queue anyway (never drop)
  │       ├─ Debug span → drop (if feature enabled)
  │       └─ Other → queue span
  └─ Queue full?
      ├─ Select spans to drop (debug first, then normal)
      ├─ Record drop metrics
      └─ Queue new span
```

### Drain Loop

A background thread periodically flushes spans to registered exporters:

```
flush_batch()
  └─ For each span in batch:
      └─ Call each exporter
          ├─ Success → continue
          └─ Failure
              ├─ Normal mode → log error, increment failure metric
              └─ Strict mode → log warning, increment failure metric
```

## Metrics

| Metric | Type | Labels |
|--------|------|--------|
| `llm_agent_telemetry_queue_depth` | Gauge | tenant_id, agent_id, priority |
| `llm_agent_telemetry_spans_dropped_total` | Counter | tenant_id, agent_id, priority, reason |
| `llm_agent_telemetry_export_failures_total` | Counter | tenant_id, agent_id, exporter |
| `llm_agent_telemetry_backpressure_active` | Gauge | tenant_id, agent_id |

## Design Decisions

- **Export never blocks runtime**: Exporter failures are logged async; the drain loop never blocks the enqueue path
- **Critical spans preserved**: Priority classification ensures security and error spans survive queue pressure
- **Multi-dimensional rate limiting**: Leaky buckets per tenant/agent/type/exporter prevent any single dimension from flooding
- **Drop metrics**: All dropped spans are counted by priority and reason for observability

## Usage

```python
from app.services.agents.telemetry.backpressure import TelemetryBackpressure

bp = TelemetryBackpressure(max_queue_size=1000)
bp.register_exporter(my_exporter_function)
bp.start_drain_loop()

bp.enqueue(
    span={"id": "span-1", "type": "model_call", "name": "llm.call"},
    tenant_id="tenant-1",
    agent_id="agent-1",
)
```
