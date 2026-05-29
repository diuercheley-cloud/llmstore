---
owner: platform-ops
status: consolidated
---

# Operações de Controle SOC 2

O `llm-inference-stack` implementa rotinas operacionais para garantir a eficácia contínua dos controles SOC 2.

## Ciclo de Operação de Controles

### 1. Revisão de Acesso (Trimestral)
- **Objetivo**: Garantir que apenas usuários autorizados possuam acesso aos sistemas críticos.
- **Evidência**: Relatório gerado por `scripts/soc2-access-review.sh` e aprovado no portal Admin.

### 2. Revisão de Mudanças (Por Release)
- **Objetivo**: Validar que todas as mudanças em produção passaram pelos gates de segurança e qualidade.
- **Evidência**: Logs de CI/CD e artefatos de validação de release.

### 3. Revisão de Incidentes (Contínua)
- **Objetivo**: Aprender com falhas e garantir que ações de remediação foram concluídas.
- **Evidência**: Timeline de incidentes e relatórios de post-mortem.

### 4. Gestão de Exceções
Casos onde um controle não pode ser aplicado devem ser formalmente registrados com uma data de expiração e justificativa técnica.
- **Exceções Vencidas**: São tratadas como gaps críticos de segurança no relatório de prontidão.
