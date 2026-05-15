# Commercial Capacity Planning & Predictive Autoscaling (Phase 21)

## Overview

Phase 21 introduces capacity planning and predictive autoscaling for the commercial routing layer. This system allows administrators to monitor cluster saturation, forecast future demand, and receive proactive recommendations for scaling and traffic management.

The system operates in **dry_run** mode by default, providing recommendations without executing real infrastructure changes.

## Components

### 1. Capacity Monitor
Captures periodic snapshots of:
- **RPM (Requests Per Minute)**
- **Concurrency**
- **Latency (Avg/P95)**
- **Resource Utilization (CPU/GPU/Memory)**
- **SLA Violation Rate**
- **Fallback & Block Rates**

### 2. Capacity Forecasting
Predicts future demand using EWMA (Exponentially Weighted Moving Average) and linear trend analysis.
- **Saturation Prediction**: Identifies when a cluster or provider will reach its capacity limit.
- **SLA Risk Analysis**: Predicts potential SLA violations based on load trends.

### 3. Autoscaling Recommendations
Generates actionable advice:
- **Scale Up**: When demand is growing and approaching capacity.
- **Scale Down**: When capacity is underutilized for an extended period.
- **Throttle**: Recommends throttling lower QoS tiers (e.g., Free) to protect Premium tiers during high load.
- **Reroute**: Suggests moving traffic to other clusters or providers.

## Configuration

Enabled via environment variables:
- `COMMERCIAL_CAPACITY_PLANNING_ENABLED=true`
- `COMMERCIAL_AUTOSCALING_MODE=dry_run`
- `COMMERCIAL_CAPACITY_FORECAST_WINDOW_MINUTES=60`
- `COMMERCIAL_CAPACITY_SNAPSHOT_INTERVAL_SECONDS=30`
- `COMMERCIAL_CAPACITY_RETENTION_DAYS=30`

## Admin API

- `GET /admin/routing/capacity/overview`: Current cluster state and recent snapshots.
- `GET /admin/routing/capacity/forecast`: Predictive data and saturation alerts.
- `GET /admin/routing/capacity/recommendations`: Active scaling recommendations.
- `POST /admin/routing/capacity/capture`: Manually trigger a snapshot.
- `POST /admin/routing/capacity/rebuild-forecast`: Force recalculation of forecasts.
- `GET /admin/routing/capacity/export`: Export data in JSON, CSV, or HTML.

## Operation

The system runs a background loop (via `distributed_analytics_loop` or similar) to capture snapshots every 30 seconds. Forecasts are typically updated every few minutes or on demand.

All recommendations are stored in the database for historical audit and can be used as a "Ready to Execute" signal for future automation phases (e.g., Kubernetes/Nomad integration).
