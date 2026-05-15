# Predictive AIOps & Failure Forecasting (Phase 66)

## Overview
Phase 66 implements a local, offline-first AIOps layer for the LLM Inference Stack. It provides automated anomaly detection, failure forecasting, and operational risk scoring without relying on external SaaS or heavy ML models.

## Key Components

### 1. Anomaly Correlation
Monitors runtime events and system metrics to identify potential issues.
- **Drift Detection:** Correlates determinism drift events from the Runtime Fabric.
- **Metric Heuristics:** Uses rolling z-scores and EWMA to detect latency and throughput anomalies.

### 2. Failure Forecasting
Predicts future system failures based on current trends.
- **Node Exhaustion:** Predicts node failure when CPU/Memory usage exceeds 90%.
- **GPU Thermal/Power:** Clusters anomalies to predict GPU degradation.
- **Queue Saturation:** Forecasts potential bottlenecks in the QoS priority queues.

### 3. Runtime Risk Scoring
Aggregates anomalies and forecasts into a unified operational risk score.
- **Trend Analysis:** Identifies if the system risk is increasing, decreasing, or stable.
- **Contributing Factors:** Links risks back to specific system events for auditability.

### 4. Auto-remediation Recommendations
Generates advisory actions to mitigate predicted risks.
- **scale_up / isolate_node:** For resource issues.
- **throttle_tenant:** For QoS fairness.
- **replay_workflow:** For drift correction.

## Technical Architecture
- **Offline-First:** Runs entirely on-premises, compatible with air-gapped environments.
- **Deterministic Heuristics:** Uses explainable math instead of black-box ML.
- **Immutable Audit:** All predictions and recommendations are hashed and stored for governance.

## API Endpoints
- `GET /admin/aiops/status`: Current engine state.
- `GET /admin/aiops/forecasts`: Active failure predictions.
- `GET /admin/aiops/anomalies`: Detected anomaly signals.
- `GET /admin/aiops/recommendations`: Suggested actions.
- `POST /admin/aiops/run-cycle`: Manual trigger for the AIOps engine.

## Configuration
Controlled via standard environment variables:
- `AIOPS_ENABLED=true`
- `AIOPS_SOVEREIGN_MODE=true`
