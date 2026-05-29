---
owner: platform-ops
status: consolidated
---

# Golden Tasks

## Overview

Golden Tasks are high-priority evaluation cases that represent critical functionality or "happy path" scenarios that MUST always work correctly.

## Enforcement

If an evaluation case is marked as `is_golden: true`, the promotion gate will fail if this specific case does not pass, regardless of the overall pass rate. 

This prevents agents from being promoted if they fail at their core mission, even if they pass most other tests.

## Adding Golden Tasks

When creating or updating a dataset version, set `"is_golden": true` on critical cases.

```json
{
  "name": "Process Refund",
  "input_text": "Refund order #123",
  "is_golden": true,
  "assertions": [...]
}
```
