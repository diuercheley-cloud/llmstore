# Deploying vLLM in Production

This guide outlines deployment strategies, hardware considerations, and operational monitoring when integrating vLLM with the `llm-inference-stack`.

## Deployment Topology

vLLM is typically deployed as a standalone container or a Kubernetes pod running alongside the control plane.

```
+-----------------------------------+
|       Control Plane API           |
+-----------------------------------+
                  |
        (HTTP /v1 completions)
                  v
+-----------------------------------+
|      vLLM Container (GPU)         |
+-----------------------------------+
```

### Running with Docker

Run the vLLM engine container, exposing port `8000`:

```bash
docker run --gpus all \
    -v ~/.cache/huggingface:/root/.cache/huggingface \
    -p 8000:8000 \
    --ipc=host \
    vllm/vllm-openai:latest \
    --model facebook/opt-125m
```

Configure the control plane environment variables:
```env
VLLM_BACKEND_ENABLED=true
VLLM_BASE_URL=http://<vllm-host>:8000/v1
VLLM_DEFAULT_MODEL=facebook/opt-125m
```

## Monitoring Health and Metrics

*   **Healthchecks**: The control plane administrative route `/admin/inference/backends/vllm/health` queries vLLM's `/health` endpoint and falls back to `/v1/models` if needed.
*   **Latency Monitoring**: Inference proxy metrics track request latency, TTFT (time-to-first-token), and overall latency per backend.
*   **Concurrences**: Track throughput via the `max_parallel_requests` configuration to ensure adequate slot allocation under peak workloads.
