---
owner: platform-ops
status: consolidated
---

# Release Notes: v1.9.6-ci-chaos

## Visão Geral
A release **v1.9.6-ci-chaos** foca na maturidade do pipeline de entrega e na resiliência da infraestrutura. Introduzimos automação rigorosa e engenharia de chaos para garantir que o `llm-inference-stack` seja estável sob estresse.

## Principais Novidades

### 1. Governança de CI/CD
- **Paridade Multi-Plataforma**: Suporte nativo para GitHub Actions e GitLab CI com jobs idênticos de validação.
- **Deploy Controlado**: Pipelines dedicadas para Appliance, Kubernetes e Enterprise Pilots com aprovação manual.

### 2. Framework de Chaos Engineering
- **Injeção Controlada**: Testes de resiliência agora são orquestrados e auditáveis via Admin UI.
- **Safety Rails**: Bloqueio nativo em produção e timeouts obrigatórios para evitar danos colaterais.

### 3. Supply Chain & Segurança
- **SBOM**: Geração de lista de materiais para auditoria de dependências.
- **Assinatura de Artefatos**: Garantia de autenticidade dos pacotes de release.
- **Secrets Scan**: Prevenção automática de vazamento de credenciais no pipeline.

## Como Atualizar
Consulte `docs/deployment/upgrade-guide.md` para instruções detalhadas sobre como migrar da v1.9.5 para a v1.9.6.
