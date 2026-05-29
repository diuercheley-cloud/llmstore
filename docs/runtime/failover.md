---
owner: platform-ops
status: consolidated
---

# Failover and Reliability

The distributed runtime is designed to be resilient to node failures.

## Detection

Node failures are detected in two ways:
1. **Missed Heartbeats**: If a node fails to send a heartbeat within 60 seconds, it is marked as `offline`.
2. **Request Failures**: If a request to a node fails with a connection error or a 5xx status code, the control plane records a failure event.

## Automatic Failover

When a node failure is detected during a request, the `InferenceProxy` or `client` service will:
1. Catch the error.
2. Record a `RuntimeFailoverEvent`.
3. Select a new healthy node for the same model.
4. Retry the request on the new node.

## Draining Mode

For maintenance, a node can be placed in `draining` mode. In this mode, the node will finish existing requests but will not receive new ones.

```bash
./scripts/runtime-node-drain.sh <node_id> <admin_token>
```
