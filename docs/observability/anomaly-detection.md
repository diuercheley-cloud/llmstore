# Agentic Anomaly Detection

The Anomaly Detection service monitors real-time agent metrics to identify significant deviations from historical performance, providing early warning for operational issues or security threats.

## Monitored Anomalies

### 1. Cost Spikes
Detects if an agent's estimated cost in the last hour exceeds a threshold multiplier (default 2.0x) compared to its previous 24-hour average. This helps identify runaway loops or inefficient prompt templates.

### 2. Tool Failure Spikes
Identifies sudden increases in the failure rate of specific tools, which may indicate API outages or regression in tool-handling logic.

### 3. Latency Spikes
Monitors p95 latency for model calls and tool executions, alerting when performance degrades significantly.

### 4. Approval Backlog
Alerts when the number of pending Human-in-the-Loop (HITL) requests grows beyond historical norms, indicating potential operational bottlenecks.

## Alerting

When an anomaly is detected, the service generates an alert event. These events can be consumed by external monitoring systems or displayed on the **Agentic Analytics Dashboard**.

## Configuration

Enable anomaly detection via feature flag:

```bash
AGENT_ANOMALY_DETECTION_ENABLED=true
```
