# Commercial Geo-Aware Latency Routing

Phase 19 introduces geographical awareness to the Global Router.

## Features

- **Distance Calculation**: Haversine formula to calculate distance between clusters.
- **Latency Penalty**: Dynamic penalty based on distance and average public latency.
- **Cross-Ocean Detection**: Heuristic to block or penalize routing across oceans.
- **Geo Scoring**: Combines distance, latency, margin, health, and region for optimal selection.

## Configuration

- `COMMERCIAL_GEO_ROUTING_ENABLED`: Master switch.
- `COMMERCIAL_GEO_RO_MODE`: `dry_run` (default), `recommend_only`, `balancing`.
- `COMMERCIAL_GEO_ROUTING_MAX_REGION_DISTANCE_KM`: Threshold for region boundaries.

## Scoring formula

```
Score = Base - (LatencyPenalty * W_lat) + (MarginScore * W_margin) + (Health * W_health) + (RegionBonus * W_reg)
```

## Admin Endpoints

- `GET /admin/routing/geo-routing/overview`: Current geo status and ranked clusters.
- `GET /admin/routing/geo-routing/recommendations`: Best geo-aware route for current cluster.
- `POST /admin/routing/geo-routing/simulate`: Simulate routing from any lat/lon.
