# Agent Evaluation Framework

## Overview

The Agent Evaluation Framework provides a uniform layer for running automated agent benchmarks and exporting reports without coupling product logic to a single evaluation harness.

## Supported benchmarks

- AgentBench
- GAIA
- BFCL

## Metrics

- Success rate
- Tool efficiency
- Latency
- Token cost
- Hallucination score

## Data flow

1. The admin API receives a benchmark request.
2. `AgentEvaluationService` resolves the benchmark task set.
3. Each task is executed through a runner, which can be replaced with a real agent execution path.
4. The service computes metrics and writes exportable artifacts.
5. The admin dashboard reads the latest reports from the artifacts directory.

## Exports

Each run generates:

- `report.json`
- `report.csv`
- `report.md`

## CI

The optional `run-agent-benchmarks` workflow input enables the benchmark job in CI for manual or scheduled validation.

