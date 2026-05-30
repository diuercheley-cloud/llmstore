# Fine-tuning Pipeline and Governance

This document describes the native Fine-tuning and MLOps capability of the `llm-inference-stack`.

## Overview
The fine-tuning service provides governed execution of training jobs using datasets versioned within the compliance registry.

## Configuration & Feature Flags
To enable Fine-tuning, the following feature flags must be enabled:
* `MLOPS_ENABLED=true`
* `FINE_TUNING_ENABLED=true`

## Lifecycle State Machine
A training job transitions through the following statuses:
1. `queued`: Job created and pending execution.
2. `running`: Job currently running (local/mock/external provider).
3. `completed`: Job finished successfully, resulting in an `output_model_id`.
4. `failed`: Job execution encountered an error.

## Log Sanitization
To prevent credential leaks, training logs are automatically scanned and sanitized prior to persistence. Any occurrences of:
* API Keys (`sk-...`)
* Bearer tokens
* Keys matching `secret`, `password`, `token`, `private_key`
are replaced with `[REDACTED_SENSITIVE_DATA]`.
