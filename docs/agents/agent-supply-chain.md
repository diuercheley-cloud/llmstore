---
owner: platform-ops
status: consolidated
---

# Agent Supply Chain Security

## Overview

The Kleber AI Platform enforces strict supply chain security for all installable agents and tools. Every bundle undergoes verification of checksums, signatures, and provenance before installation.

## Components

- **Bundles**: Self-contained packages containing manifests, definitions, and metadata.
- **Provenance**: Records of the build environment, source URL, and commit hash (SLSA-compliant metadata).
- **Trust Reports**: Aggregated security scores based on signing status, author reputation, and vulnerability scans.

## Verification Workflow

1.  **Checksum Verification**: Ensures the bundle hasn't been tampered with in transit.
2.  **Signature Check**: Validates that the bundle was signed by a verified publisher.
3.  **Compatibility Check**: Verifies that the agent is compatible with the current platform version and feature flags.
4.  **Policy Review**: Automated and manual review of tool permissions and memory policies.
