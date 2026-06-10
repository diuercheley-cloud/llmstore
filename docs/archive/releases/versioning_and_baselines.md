---
owner: platform-ops
status: consolidated
---

# Versioning and Baselines

## Versioning Strategy
We use a deterministic versioning strategy where each release is tied to a specific platform baseline hash.

## Platform Baselines
A baseline represents a stable, validated state of the entire stack.
- **Baseline ID**: Unique UUID.
- **Release Version**: Human-readable version string.
- **Scope**: Components included in the baseline.
- **Validation Hash**: Aggregate hash of all validation results.

## Replay-Safe Metadata
All release metadata is designed to be replay-safe, ensuring that the same source state always produces the same release artifacts.
