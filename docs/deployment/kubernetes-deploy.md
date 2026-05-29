---
owner: platform-ops
status: consolidated
---

# Deployment em Kubernetes (Helm)

O deployment em Kubernetes é recomendado para ambientes escaláveis e enterprise pilots.

## Estratégia de Configuração

O stack utiliza Helm para orquestração. Os manifestos são renderizados localmente antes da aplicação para auditoria.

> [!IMPORTANT]
> **Segredos**: Nunca coloque segredos reais nos arquivos de configuração do Helm. Os segredos devem ser criados manualmente no cluster ou injetados via provedores de segredos (Vault, AWS Secrets Manager) e referenciados nos manifestos.

## Fluxo de Deploy

1.  **Renderização**: Os templates do Helm são processados em `deploy/rendered/manifests.yaml`.
2.  **Validação**: Verificação sintática e de segurança dos manifestos.
3.  **Namespace**: Criação automática do namespace (default: `llm-stack`).
4.  **Aplicação**: `kubectl apply` dos manifestos.
5.  **Status**: Aguarda o `rollout status` dos deployments principais.

## Como Executar

```bash
make deploy-k8s
```

## Variáveis de Ambiente

Você pode customizar o deployment via variáveis de ambiente:
- `K8S_NAMESPACE`: Nome do namespace no cluster.
- `HELM_RELEASE`: Nome da release do Helm.
