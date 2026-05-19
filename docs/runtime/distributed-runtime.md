# Distributed Runtime

The LLM Inference Stack supports a real multi-node distributed runtime mode. This allows you to have multiple data plane nodes running on different physical or virtual machines, edge devices, or Kubernetes pods, all managed by a single control plane.

## Architecture

- **Control Plane**: Manages node registration, health checks, model placement, and routing.
- **Data Plane Nodes**: Execute the actual LLM inference. Each node registers itself with the control plane and sends periodic heartbeats.

## Routing Strategies

- `least_load`: Routes requests to the node with the fewest active requests.
- `gpu_priority`: Prioritizes nodes with more GPU resources.
- `round_robin`: Simple sequential distribution.

## High Availability

The control plane automatically detects node failures through missed heartbeats and routes around them. If a node becomes unhealthy during a request, the control plane can automatically failover to another available node.
