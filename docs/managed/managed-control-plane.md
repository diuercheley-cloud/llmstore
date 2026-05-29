# Managed Control Plane

The Managed Control Plane subsystem connects a local appliance to an upstream centralized control plane.

## Metadata-Only Sync
To preserve tenant privacy, only operational metadata is synchronized (e.g. queue depth, error rates, readiness state).
Prompts, memory, and documents are strictly filtered out by the Data Boundary Policy.

## Opt-in Features
Policy sync from the managed control plane is entirely opt-in via the `MANAGED_CONTROL_PLANE_ENABLED` flag and `sync_policies` configuration.
