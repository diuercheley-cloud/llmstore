# Commercial Cost-Aware Live Balancing

Phase 19 introduces adaptive traffic rebalancing based on real-time margin and latency.

## Features

- **Profitability Analysis**: Continuous monitoring of cluster margins.
- **Dynamic Rebalancing**: Gradual traffic shifting to optimize costs.
- **Anti-Flapping**: Hysteresis and stability windows to prevent oscillation.
- **Dry-Run Mode**: Simulation and recommendations without automatic changes.

## Anti-Flapping Protection

- **Hysteresis**: Minimum change threshold (e.g. 10%) before action is taken.
- **Stable Window**: Minimum time (e.g. 30 mins) between changes for the same cluster.
- **Cooldown**: Prevents rapid successive changes.

## Admin Endpoints

- `GET /admin/routing/live-balancing/overview`: Current balancing status.
- `GET /admin/routing/live-balancing/opportunities`: List of potential rebalance actions.
- `POST /admin/routing/live-balancing/simulate`: Test balancing logic against custom metrics.
