# Universal Inference Router

## Goal

The universal inference router normalizes backend selection and capability reporting across local and remote runtimes.

## Backends

Supported backend families:

- `ollama`
- `llama.cpp`
- `vLLM`
- `TGI`
- `TensorRT-LLM`
- `MLX`

These backends are represented as `InferenceBackend` records in the control plane and exposed through a common capability contract.

## Capability contract

The router exposes one logical capability model:

- streaming
- embeddings
- tool calling
- vision
- batching

Capability support is derived from provider metadata and backend classification rules, rather than from ad hoc branching in request handlers.

## Benchmarking

Each backend gets a lightweight automatic benchmark:

- health check result
- model listing availability
- response latency
- capability score

The benchmark is intentionally cheap. It is meant for routing decisions and operator visibility, not for full model evaluation.

## API surface

`GET /api/backends/capabilities` returns:

- backend list
- normalized capability flags
- benchmark summary
- aggregate totals for operator dashboards

## Extension path

To add a new backend family, extend the router capability map and keep the request-path logic untouched. The point is to keep provider-specific differences at the edge, not in business services.
