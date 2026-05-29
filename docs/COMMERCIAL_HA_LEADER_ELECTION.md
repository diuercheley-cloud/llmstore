---
owner: platform-ops
status: consolidated
---

# Commercial HA / Leader Election

`llm-inference-stack` Phase 14 adds database-backed commercial high availability without Redis, Kafka or ZooKeeper.

## Architecture

- Shared database stores `commercial_leader_leases`
- Each critical commercial role owns a short lease
- Roles supported: `scheduler`, `aggregator`, `reporter`, `calibration`, `canary`, `global`
- Node liveness comes from `commercial_node_heartbeats`
- Critical write paths validate fencing tokens before destructive work

## Lease Model

- A leader acquires a lease row for `(cluster_id, leader_role)`
- Only one `active` lease is allowed logically and by partial unique index
- Lease fields:
  - `lease_token`: monotonically increasing fencing token
  - `lease_acquired_at`
  - `lease_expires_at`
  - `last_heartbeat_at`
  - `status`: `active`, `expired`, `released`
- Recommended defaults:
  - `COMMERCIAL_LEADER_ELECTION_ENABLED=true`
  - `COMMERCIAL_LEASE_DURATION_SECONDS=60`
  - `COMMERCIAL_LEASE_HEARTBEAT_SECONDS=15`
  - `COMMERCIAL_LEASE_RENEW_BEFORE_SECONDS=20`
  - `COMMERCIAL_LEASE_MAX_CLOCK_SKEW_SECONDS=5`
  - `COMMERCIAL_LEADER_FENCING_ENABLED=true`

## Heartbeat

- Nodes already publish `commercial_node_heartbeats`
- Lease expiration also considers stale/offline heartbeats
- If a leader stops heartbeating, other nodes can expire the stale lease and promote a new leader

## Fencing Token

- `lease_token` is issued on lease acquisition and increases on each takeover/failover
- Critical jobs must pass the current token before destructive actions
- If the token is stale, execution is rejected and audited as `fencing_rejected`
- This prevents split-brain when an old node keeps running after losing the lease

## Failover

Flow:

1. Active leader stops renewing or its node heartbeat goes offline
2. Lease becomes stale and is marked `expired`
3. Another node acquires the same role
4. New node receives a higher `lease_token`
5. Old node loses write authority immediately because fencing validation fails

## Protected Jobs

- `rebuild_aggregates`
- `cleanup_old_analytics`
- report scheduling
- calibration recommendation jobs
- calibration auto-apply jobs
- canary promotion / rollback jobs

## Admin Endpoints

- `GET /admin/routing/ha/leaders`
- `GET /admin/routing/ha/cluster-state`
- `POST /admin/routing/ha/force-expire`
- `POST /admin/routing/ha/release`
- `POST /admin/routing/ha/acquire`

Returned data includes:

- current leader per role
- lease expiration
- fencing token
- heartbeat age
- stale leaders
- recent failover-related audit events

## Split-Brain Prevention

- partial unique active lease per role
- short leases
- explicit renew
- node heartbeat expiration
- fencing validation before destructive work

## Single-Node Compatibility

- If election is disabled, the stack remains operational
- APIs do not crash when lease acquisition fails
- Followers stay idle instead of forcing process termination

## Limitations

- Safety depends on all critical job paths validating fencing tokens
- Very long-running tasks should validate fencing again before final commit/write
- Failover timing depends on lease duration and heartbeat cadence

## Troubleshooting

- Leader not moving:
  - check `commercial_node_heartbeats`
  - call `POST /admin/routing/ha/force-expire`
- Repeated fencing rejection:
  - confirm only the current token is used
  - inspect `/admin/routing/ha/cluster-state`
- Unexpected idle follower:
  - inspect leader for the target role
  - verify `CLUSTER_ID`, `NODE_ID` and `NODE_ROLE`

## Multi-Node Operation

- Keep all nodes on the same shared database
- Configure stable `NODE_ID` and shared `CLUSTER_ID`
- Keep clock skew low even though the lease model tolerates a small configured skew
- Use the HA dashboard section to confirm active roles and failovers
