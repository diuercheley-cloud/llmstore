---
owner: platform-ops
status: consolidated
---

# Kubernetes Installation Guide

This guide describes how to install the LLM Inference Stack on Kubernetes.

## Prerequisites

- Kubernetes cluster 1.25+
- `kubectl` installed
- `helm` 3.0+ (optional for chart installation)

## Installation using Manifests

```bash
kubectl apply -f deploy/kubernetes/pvc.yaml
kubectl apply -f deploy/kubernetes/config.yaml
kubectl apply -f deploy/kubernetes/crds.yaml
kubectl apply -f deploy/kubernetes/services.yaml
kubectl apply -f deploy/kubernetes/deployments.yaml
kubectl apply -f deploy/kubernetes/extras.yaml
```

## Installation using Helm

```bash
helm install llm-stack deploy/helm/llm-inference-stack
```

## Configuring Ingress

Update `deploy/kubernetes/extras.yaml` or use Helm `values.yaml` to configure your ingress host.
