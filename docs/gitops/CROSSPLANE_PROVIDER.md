# Crossplane Provider: LLM Stack

Gerencie o ciclo de vida dos seus agentes e tenants diretamente via Kubernetes.

## Custom Resource Definitions (CRDs)

- `Tenant`: Representa uma conta de cliente isolada.
- `Agent`: Define um agente de IA configurado.
- `Policy`: Regras de governança centralizadas.
- `ModelRoute`: Estratégias de roteamento inteligentes.

## Exemplo YAML

```yaml
apiVersion: llmstack.kleber.ai/v1alpha1
kind: Tenant
metadata:
  name: marketing-dept
spec:
  name: "Marketing"
  description: "Marketing team resources"
```

## Benefícios GitOps

- Reconciliação contínua de estado.
- Governança via repositório Git.
- Integração nativa com ecossistema Cloud Native.
