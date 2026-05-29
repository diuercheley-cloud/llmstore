# Sovereign Memory Sync

## Sovereignty Model
The "Sovereign Control Plane" ensures that knowledge sharing between clusters respects national and organizational boundaries.

### 1. Residency Enforcement
The `SovereigntyPolicy` service maintains a mapping of data types to prohibited regions. 
- **Example**: Sensor telemetry originating from EU clusters cannot be synchronized to clusters located in regions with different data protection laws unless a `sovereign` trust relationship exists.

### 2. Tenant & Cluster Boundaries
- Each federated record (summary, fact, or reference) is tagged with both the `origin_cluster_id` and the `tenant_id`.
- Agents can only retrieve federated knowledge that matches their own `tenant_id` and is authorized by the local cluster's policy.

### 3. Revocation & Compliance
To comply with global privacy standards (e.g., GDPR, LGPD), revocation must be global.
- When an `erasure_request` is completed locally, a `revocation_propagation` event is emitted.
- Federated peers receiving this event must immediately set `is_valid = false` on all related `RemoteMemoryReference` records and delete cached summaries.

### 4. Cryptographic Proofs
Sync events include provenance metadata and hashes. This allows auditors to verify that the synchronized knowledge was indeed originated from a trusted peer and has not been tampered with in transit.
