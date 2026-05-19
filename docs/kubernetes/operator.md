# Kubernetes Operator

 The LLM Inference Stack Operator automates the management of the stack components.

## Features

- Automatic reconciliation of Deployments and Services.
- Management of Custom Resources (LLMInferenceStack, LLMModelRuntime).
- Health monitoring and status reporting.

## Running the Operator

```bash
# In-cluster
kubectl apply -f deploy/kubernetes/operator-deployment.yaml

# Local development
kopf run operator/main.py
```
