# vLLM Inference Backend

The vLLM backend provides high-performance, native inference compatibility within the `llm-inference-stack` using the OpenAI-compatible API.

## Configuration & Feature Flags

To activate and configure the vLLM backend, set the following environment variables:

*   `VLLM_BACKEND_ENABLED` (Default: `false`): Feature flag to enable or disable the vLLM backend.
*   `VLLM_OPENAI_COMPAT_ENABLED` (Default: `false`): Enables utilizing OpenAI compatibility mode.
*   `VLLM_BASE_URL` (Default: `http://localhost:8000/v1`): The base URL of the running vLLM server.
*   `VLLM_API_KEY` (Default: `""`): Optional API Key used to authenticate with the vLLM instance.
*   `VLLM_DEFAULT_MODEL` (Default: `facebook/opt-125m`): The default model registry ID to bind for completions.
*   `VLLM_TIMEOUT_SECONDS` (Default: `120`): Maximum time to wait for a generation response.
*   `VLLM_MAX_CONCURRENT_REQUESTS` (Default: `16`): Maximum parallel generation slots allowed on this backend.

## Registration & Routing

When `VLLM_BACKEND_ENABLED=true` is set, a default `vllm-local` backend registry entry is initialized. Models configured to route through vLLM will automatically map to the vLLM backend adapter.

*   **Smart Routing**: The `SmartRouter` includes `vllm` in local-first routing strategies and fallback orders.
*   **Failover & Fallback**: If the vLLM instance is determined to be unhealthy (or timeout occurs), the router falls back to alternative configured backends such as `llama.cpp` or cloud providers based on the plan.
*   **Quota Enforcement**: Request quotas and margin constraints are checked prior to dispatching requests to the backend.
