---
owner: platform-ops
status: consolidated
---

# Runtime Model Integrity

Phase 39 adds continuous runtime integrity monitoring for signed model artifacts already managed by the supply-chain controls.

## What It Covers

- periodic re-hash of active runtime models
- runtime drift detection for checksum and manifest changes
- file swap and tampering detection
- alias drift detection when runtime alias points to a different manifest or file
- boot attestation snapshots for active models
- integrity timeline with audit events
- federated integrity status summary without filesystem disclosure

## Components

- `CommercialModelIntegrityScan`
  - stores boot, scheduled, manual, runtime validation, and federated scan results
- `CommercialRuntimeModelAttestation`
  - stores expected vs observed manifest and checksum snapshots from runtime
- `CommercialModelIntegrityEvent`
  - stores immutable audit events for scans, drift, missing files, quarantine, and alias drift

## Config

```env
COMMERCIAL_MODEL_INTEGRITY_MONITOR_ENABLED=true
COMMERCIAL_MODEL_INTEGRITY_SCAN_INTERVAL_SECONDS=3600
COMMERCIAL_MODEL_INTEGRITY_AUTO_QUARANTINE=false
COMMERCIAL_MODEL_INTEGRITY_BOOT_SCAN_ENABLED=true
```

## Scan Modes

- `boot`
  - runs during control-plane startup when enabled
- `scheduled`
  - runs in the background monitor loop using HA-aware singleton leadership
- `manual`
  - triggered by admin endpoint
- `runtime_validation`
  - used for targeted re-verification
- `federated`
  - reserved for peer-integrity replication summaries

## Runtime Attestation

Runtime attestation compares:

- signed registry manifest hash vs runtime-observed manifest hash
- signed registry checksum vs runtime-observed checksum
- expected alias and runtime alias
- expected signed file vs runtime-served file

Attestation states:

- `verified`
- `drift`
- `unknown`
- `quarantined`

## Drift Rules

- missing runtime file => `missing`
- checksum mismatch => `drift_detected`
- manifest mismatch => runtime drift
- alias serving different manifest/file => alias drift
- repeated failures can trigger quarantine when auto-quarantine is enabled
- active revoked checksum records can quarantine regardless of report-only posture

## Auto Quarantine

When enabled, the monitor can move a signed registry entry to `trust_state=quarantined` and mark the runtime model as `status=quarantined` for:

- checksum mismatch
- manifest mismatch
- repeated scan failures
- active revoked checksum or CRL-style revocation

Routing blocks quarantined models only when supply-chain enforcement is set to `enforce`. In `report_only`, requests continue and the drift is recorded.

## Federation Integration

The integrity status summary includes federated peer metadata derived from governance federation records:

- peer cluster id
- status
- environment
- region

No absolute paths, full checksums, or filesystem-sensitive payloads are exposed in federated summaries.

## Admin Endpoints

- `GET /admin/models/integrity/scans`
- `POST /admin/models/integrity/scan`
- `GET /admin/models/integrity/events`
- `GET /admin/models/integrity/attestations`
- `POST /admin/models/integrity/quarantine/{id}`
- `POST /admin/models/integrity/reverify/{id}`
- `GET /admin/models/integrity/status`

## Portal Exposure

Tenant-facing model views expose only:

- runtime trust state
- quarantine status
- integrity summary
- attestation summary

They do not expose:

- absolute model paths
- full checksums
- raw filesystem details

## Limitations

- this is not formal secure boot
- runtime manifest comparison uses local control-plane runtime metadata and signed registry expectations
- no cloud scanner is required
- report-only mode records drift without globally blocking traffic
