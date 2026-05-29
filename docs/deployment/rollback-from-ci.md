---
owner: platform-ops
status: consolidated
---

# Rollback via CI/CD

A segurança da operação é baseada na capacidade de voltar atrás rapidamente.

## Rollback Automático
Se o job de `post-deploy-validate` falhar, a pipeline executará automaticamente o comando `make rollback-release`.

## Rollback Manual
Se uma instabilidade for detectada após a conclusão da pipeline, o operador pode disparar o job de rollback manualmente através da interface de CI/CD.
