---
owner: platform-ops
status: consolidated
---

# Sovereign Offline AI Appliance Mode

## Overview
Phase 52 transforms the LLM Inference Stack into an "Offline-First" Sovereign Appliance. This mode is designed for fully air-gapped environments, defense systems, government agencies, and highly regulated enterprises that require physical isolation from the internet.

## Key Concepts

### 1. Appliance Profiles
Every deployment gets a unique `CommercialApplianceProfile`. This defines the deployment tier (e.g., `defense`, `airgap`) and enforces offline rules, such as requiring hardware validation for data transfers.

### 2. Offline Sync Manifests
Since the appliance cannot pull models or push audit logs via APIs, all data transfers occur via **Removable Media**. A `CommercialOfflineSyncManifest` tracks every import (models, policies) and export (audit logs, cryptographic receipts).

### 3. Removable Media Chain of Custody
If `commercial_appliance_require_removable_media` is enabled, the appliance reads the unique hardware UUID of the USB/Drive used for transfer. It will reject sync operations if the media UUID does not match authorized cryptographic records.

### 4. Offline Model Bundles
Models are delivered as encrypted bundles (`CommercialOfflineModelBundle`). They are imported in a `staged` status. Once signatures are verified against the pre-loaded Sovereign Registry, they are `promoted` and become available for inference.

### 5. Audit Packages
The appliance generates `CommercialOfflineAuditPackage`s. These contain all cryptographic receipts, workflow proofs, and agent governance logs for a specific time window, ready to be safely exported to physical media.

## Configuration
- `COMMERCIAL_APPLIANCE_MODE_ENABLED`: Enable appliance features.
- `COMMERCIAL_APPLIANCE_ID`: Unique identifier for the hardware node.
- `COMMERCIAL_APPLIANCE_DEPLOYMENT_TIER`: Set to `airgap`, `government`, `defense`, or `regulated`.
- `COMMERCIAL_APPLIANCE_REQUIRE_REMOVABLE_MEDIA`: Enforce physical media UUID checks.

## API Endpoints
- `GET /admin/inference/appliance/status`: Appliance health and configuration.
- `GET /admin/inference/appliance/manifests`: List import/export operations.
- `GET /admin/inference/appliance/bundles`: View staged and promoted offline models.
- `POST /admin/inference/appliance/audit-packages`: Generate a new export package for compliance.
