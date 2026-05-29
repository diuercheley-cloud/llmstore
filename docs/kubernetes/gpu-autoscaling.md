---
owner: platform-ops
status: consolidated
---

# GPU Autoscaling em Kubernetes

Em clusters Kubernetes, o LLM Inference Stack integra-se com o Horizontal Pod Autoscaler (HPA) ou utiliza seu próprio controlador customizado.

## Integração com Device Plugin

O orquestrador detecta GPUs alocadas via `nvidia.com/gpu` e monitora a utilização dentro dos pods.

## Escalonamento de Nós

Se não houver recursos de GPU disponíveis no cluster para um novo scale up, o stack pode disparar alertas para o Cluster Autoscaler do provedor de nuvem.
