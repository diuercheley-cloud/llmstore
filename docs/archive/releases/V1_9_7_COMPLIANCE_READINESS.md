---
owner: platform-ops
status: consolidated
---

# Release Notes: v1.9.7-compliance-readiness

## Visão Geral
A release **v1.9.7-compliance-readiness** introduz uma camada profunda de governança e conformidade regulatória no `llm-inference-stack`. Focamos em automatizar a prontidão para auditorias SOC 2 e ISO 27001, garantindo que o operador tenha todas as ferramentas para provar a segurança da sua infraestrutura de IA.

## Principais Novidades

### 1. Governança ISMS (ISO 27001)
- **ISMS-Lite**: Sistema de gestão de segurança integrado com políticas, gestão de riscos e Declaração de Aplicabilidade (SoA).
- **Políticas Digitais**: 12 políticas fundamentais prontas para revisão e aprovação.

### 2. Prontidão SOC 2
- **Controle de Operações**: Rotinas para revisões de acesso, mudanças e incidentes.
- **Evidence Collector**: Coleta automática e sanitizada de evidências técnicas com validação de integridade SHA-256.

### 3. Continuous Compliance
- **CI/CD Gates**: O pipeline agora valida a conformidade das políticas e a integridade do registro de riscos em cada Pull Request.
- **Audit Packages**: Geração de pacotes de auditoria lacrados e sanitizados via `make compliance-evidence`.

### 4. Experiência Administrativa
- **Compliance Dashboard**: Nova interface executiva no Admin v2 para acompanhamento de scores de prontidão e gaps de auditoria.

## Segurança e Privacidade
- **Zero-Secret Evidence**: Todas as evidências passam por um scanner de sanitização obrigatório.
- **Readiness-Only**: O sistema foca em preparação e mapeamento de controles, sem emitir certificados formais autonomamente.

## Como Atualizar
Consulte `docs/compliance/readiness-framework.md` para instruções sobre como ativar e operar os novos módulos de conformidade.
