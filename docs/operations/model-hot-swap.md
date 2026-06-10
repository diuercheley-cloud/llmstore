---
owner: platform-ops
status: consolidated
---

# Model Hot Swap

The LLM Inference Stack supports dynamic loading, unloading, and switching of GGUF models without restarting the data plane container.

## How it works

When `MODEL_HOT_SWAP_ENABLED=true`, the control plane acts as a supervisor for multiple `llama-server` processes. Each model is loaded onto its own internal port.

### Safe Swap Flow

1. **Load**: A new model is started on a free port.
2. **Health Check**: The system waits for the new process to be ready (up to `MODEL_LOAD_TIMEOUT_SECONDS`).
3. **Activate**: Once ready, the admin can activate the model. The router will then direct all new traffic for that model-backend combination to the new port.
4. **Rollback**: If the new model fails or performs poorly, the admin can rollback to the previous ready instance.

## Configuration

- `MODEL_HOT_SWAP_ENABLED`: Enable hot swap support (default: `false`).
- `MODEL_RUNTIME_PORT_START`: Starting port for dynamic runtimes (default: `18081`).
- `MODEL_RUNTIME_PORT_END`: Ending port (default: `18120`).
- `MODEL_LOAD_TIMEOUT_SECONDS`: Time to wait for a model to become healthy (default: `120`).
- `MODEL_ROLLBACK_ON_FAILURE`: Automatically rollback if a new load fails (planned).

## Management via CLI

Use the provided scripts in `scripts/`:

- `./scripts/dev/model-runtime-list.sh`: List all loaded runtimes.
- `./scripts/dev/model-runtime-load.sh <model_id> <backend_id> <model_path>`: Load a new model.
- `./scripts/deploy/model-runtime-activate.sh <instance_id>`: Activate a loaded instance.
- `./scripts/dev/model-runtime-rollback.sh <model_id> <backend_id>`: Rollback to the previous instance.

## Management via Admin API

- `GET /admin/models/runtime`: List runtimes.
- `POST /admin/models/runtime/load`: Load a model.
- `POST /admin/models/runtime/activate/{instance_id}`: Activate an instance.
- `POST /admin/models/runtime/rollback`: Rollback.
- `GET /admin/models/runtime/{instance_id}/health`: Check instance health.
