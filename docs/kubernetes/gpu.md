---
owner: platform-ops
status: consolidated
---

# GPU Support in Kubernetes

To enable GPU support, ensure your cluster has the NVIDIA Device Plugin installed.

## Configuration

In `LLMModelRuntime` or Helm `values.yaml`:

```yaml
gpu:
  enabled: true
  count: 1
```

The operator will add the necessary resource limits and reservations to the data-plane pods.
