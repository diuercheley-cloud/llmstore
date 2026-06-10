# Integrations Manifest

Este documento mapeia as integrações do `llm-inference-stack` e prepara sua extração para repositórios independentes.

| Nome | Linguagem | Dependências | Pipeline Target | Estratégia de Extração |
| :--- | :--- | :--- | :--- | :--- |
| **VS Code Extension** | TypeScript | Node.js, VSCE | `integration-vscode` | Mover para `github.com/kleberai/vscode-llmstack` |
| **Terraform Provider** | Go | Terraform Plugin SDK v2 | `integration-terraform` | Mover para `github.com/kleberai/terraform-provider-llmstack` |
| **Crossplane Provider** | YAML/CRDs | Crossplane v1.x | `integration-crossplane` | Mover para `github.com/kleberai/provider-llmstack` |

## Princípios de Separação

1. **Build Isolado**: Cada pasta possui seu próprio `Makefile`. O CI raiz deve apenas delegar chamadas para esses Makefiles.
2. **Dependência Zero de Backend**: As integrações devem interagir com o Control Plane apenas via API REST estável, sem importar código Python interno.
3. **Versionamento Independente**: Cada integração terá seu próprio ciclo de release, seguindo as versões da API estável da plataforma.

## Como testar localmente

```bash
cd integrations/<nome>
make build
make test
```
