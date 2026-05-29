---
owner: platform-ops
status: consolidated
---

# Versioned Evaluation Datasets

## Overview

Datasets are collections of evaluation cases used to verify agent behavior. To ensure reproducibility, datasets are versioned and immutable.

## Immutability

Once a dataset version is created (e.g., `1.0.0`), it cannot be modified. If cases need to be added or changed, a new version must be created. This ensures that a baseline set today remains valid for comparison in the future.

## API Usage

### Create Dataset

```bash
POST /admin/agent-evals/datasets
{
  "agent_id": "...",
  "name": "Production Suite"
}
```

### Create Version

```bash
POST /admin/agent-evals/datasets/{id}/versions
{
  "version": "1.0.0",
  "cases_json": [...]
}
```
