# Agentic Multi-Cluster

The Multi-Cluster subsystem allows agentic platform nodes to be federated.

## Setup
Requires `MULTI_CLUSTER_ENABLED=true` and `AGENT_CLUSTER_FEDERATION_ENABLED=true`.

## Features
- **Cluster Status**: Retrieves operational status of federated clusters.
- **Manual Failover**: Operators can trigger failovers across clusters.
- **Split-brain Protection**: Default policies require a quorum or manual intervention to prevent split-brain auto-failover.
