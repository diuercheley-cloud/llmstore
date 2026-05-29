---
owner: platform-ops
status: consolidated
---

# Node Registration

Nodes can register themselves with the control plane using the registration endpoint.

## Registration Process

1. Node starts up.
2. Node sends a POST request to `/runtime/nodes/register`.
3. Control plane records the node and returns its unique ID.
4. Node begins sending heartbeats to `/runtime/nodes/{id}/heartbeat`.

## CLI Tool

You can manually register a node using the provided script:

```bash
./scripts/runtime-node-register.sh "worker-node-1" "http://192.168.1.10:8081"
```
