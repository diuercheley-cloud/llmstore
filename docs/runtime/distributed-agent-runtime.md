# Distributed Agent Runtime

The Distributed Agent Runtime is an optional execution fabric for placing agentic workloads across multiple nodes or clusters.

## Architecture
- **Job Placement**: Jobs are evaluated for GPU requirements and data residency rules. The policy defaults to `local_first` execution.
- **Distributed Leases**: Leases ensure a job is not executed concurrently by multiple nodes. Leases automatically expire, making jobs available again for failover.
- **Failover**: Allows manual failover of a job from one node to another. Opt-in policies support automatic failover.

## Endpoints
- `/admin/distributed-runtime/clusters`: Manage clusters
- `/admin/distributed-runtime/nodes`: Manage nodes
- `/admin/distributed-runtime/jobs`: List jobs
- `/admin/distributed-runtime/jobs/{id}/failover`: Trigger failover
