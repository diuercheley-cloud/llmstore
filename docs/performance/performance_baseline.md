---
owner: platform-ops
status: consolidated
---

# Performance Baseline

## Overview
This document records the baseline performance metrics for the platform. This is used to detect regressions in future releases.

## Core Metrics (Baseline v1.0.0-rc1)
- **Startup Time**: ~1.2s (Internal control plane)
- **Hashing Speed**: ~0.05ms (SHA-256 for 1KB payload)
- **Replay Verification**: ~10ms (100 receipts)
- **API Latency (Auth)**: ~5ms (Internal validation)
- **Validation Suite**: ~45s (Smoke), ~180s (Full)

## Target Baselines
| Metric | Threshold | Priority |
|--------|-----------|----------|
| Startup | < 2s | HIGH |
| Hashing | < 0.1ms | MEDIUM |
| Replay | < 50ms | HIGH |
| Smoke Suite | < 60s | HIGH |
