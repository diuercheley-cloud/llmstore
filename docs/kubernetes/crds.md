# Custom Resource Definitions (CRDs)

## LLMInferenceStack

Main resource to define a full stack instance.

```yaml
apiVersion: llm.stack.local/v1
kind: LLMInferenceStack
metadata:
  name: my-stack
spec:
  replicas: 1
  demoMode: false
```

## LLMModelRuntime

Defines a specific model runtime (data-plane).

```yaml
apiVersion: llm.stack.local/v1
kind: LLMModelRuntime
metadata:
  name: gemma-7b
spec:
  modelFile: "/models/gemma-7b.gguf"
  gpu:
    enabled: true
    count: 1
```
