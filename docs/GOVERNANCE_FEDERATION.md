# Enterprise Multi-Region Governance Federation

## Architecture

The Governance Federation framework synchronizes policies and audit trails across multiple clusters and regions, ensuring compliance consistency without a single point of failure.

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Cluster A     │     │   Cluster B     │     │   Cluster C     │
│   us-east-1     │◄───►│   eu-west-1     │◄───►│   ap-southeast  │
│                 │     │                 │     │                 │
│  ┌───────────┐  │     │  ┌───────────┐  │     │  ┌───────────┐  │
│  │ Federation│  │     │  │ Federation│  │     │  │ Federation│  │
│  │  Service  │  │     │  │  Service  │  │     │  │  Service  │  │
│  └───────────┘  │     │  └───────────┘  │     │  └───────────┘  │
│        │        │     │        │        │     │        │        │
│  ┌───────────┐  │     │  ┌───────────┐  │     │  ┌───────────┐  │
│  │  Policy   │  │     │  │  Policy   │  │     │  │  Policy   │  │
│  │  Registry │  │     │  │  Registry │  │     │  │  Registry │  │
│  └───────────┘  │     │  └───────────┘  │     │  └───────────┘  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## Components

### 1. Governance Federation Peers

Each peer represents a remote cluster with governance capabilities:

| Field | Description |
|-------|-------------|
| `peer_cluster_id` | Unique identifier for the peer cluster |
| `region` | Geographic region (e.g., us-east-1, eu-west-1) |
| `environment` | Deployment environment (production, staging, etc.) |
| `status` | active, degraded, offline, or disabled |
| `sync_mode` | pull, push, hybrid, or manual |
| `trust_level` | trusted, limited, or readonly |
| `last_policy_sync_at` | Timestamp of last policy synchronization |
| `last_audit_sync_at` | Timestamp of last audit event synchronization |

### 2. Sync Modes

| Mode | Description |
|------|-------------|
| `manual` | Sync is triggered manually via API or dashboard |
| `pull` | Local cluster pulls policies from the peer |
| `push` | Peer pushes policies to the local cluster |
| `hybrid` | Combination of pull and push modes |
| `disabled` | No synchronization occurs |

### 3. Signed Bundles

Policy bundles are signed using SHA-256 before export to peers:

- Signature validates bundle integrity during ingest
- Requires `COMMERCIAL_GOVERNANCE_FEDERATION_REQUIRE_SIGNATURE=true` to enforce
- Shared token is used as the signing key (never exposed in API responses)

### 4. Trust Levels

| Level | Description |
|-------|-------------|
| `trusted` | Full read/write access; policies can be enforced |
| `limited` | Policies received require local approval before activation |
| `readonly` | Can only receive policies; cannot enforce without local approval |

### 5. Conflict Detection

When the same bundle name and version exist in both clusters with different hashes:

```
# Conflict detection logic
same bundle_name + same bundle_version + different immutable_hash = CONFLICT
```

Conflicts can be resolved by:
- `accept_remote`: Accept the remote version
- `keep_local`: Keep the local version

### 6. Federated Audit Trail

Supported event types:
- `policy_published`
- `policy_activated`
- `rollback`
- `drift`
- `approval`
- `evidence_package`
- `exception`

Events are deduplicated using a composite key: `{source_cluster_id}:{event_type}:{source_event_id}`

### 7. Consistency Reports

The consistency check detects:
- Missing policy in a region
- Divergent bundle version
- Divergent bundle hash
- Unresolved drift
- Offline peers

## Security

- Shared tokens required for all ingest operations (configurable)
- Signature validation required for policy bundles (configurable)
- Payload sanitization removes secrets from metadata and event payloads
- Tenant-scoped bundles only replicate to authorized peers
- Limited/readonly peers cannot auto-activate enforced policies

## Configuration

```env
COMMERCIAL_GOVERNANCE_FEDERATION_ENABLED=false
COMMERCIAL_GOVERNANCE_FEDERATION_MODE=disabled
COMMERCIAL_GOVERNANCE_FEDERATION_CLUSTER_ID=local
COMMERCIAL_GOVERNANCE_FEDERATION_REGION=local
COMMERCIAL_GOVERNANCE_FEDERATION_REQUIRE_SIGNATURE=true
COMMERCIAL_GOVERNANCE_FEDERATION_REQUIRE_TOKEN=true
COMMERCIAL_GOVERNANCE_FEDERATION_SHARED_TOKEN=
COMMERCIAL_GOVERNANCE_FEDERATION_SYNC_INTERVAL_SECONDS=300
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/admin/governance/federation/peers` | List all registered peers |
| POST | `/admin/governance/federation/peers` | Register a new peer |
| POST | `/admin/governance/federation/sync` | Manually sync a policy bundle to a peer |
| POST | `/admin/governance/federation/ingest-policy` | Ingest a policy bundle from a peer |
| POST | `/admin/governance/federation/ingest-audit` | Ingest audit events from a peer |
| GET | `/admin/governance/federation/status` | Get federation status summary |
| GET | `/admin/governance/federation/consistency` | Get consistency report |
| GET | `/admin/governance/federation/audit-trail` | Get federated audit trail summary |
| GET | `/admin/governance/federation/export?format=json|csv|html` | Export federation report |

## Limits

- Federation is disabled by default
- Auto-activation of received policies does not occur in manual mode
- Limited/readonly peers require local approval for enforce mode
- Token is never exposed in responses
- Maximum export limit: 500 events per request
- Maximum sync records returned: 100
