# Controle de Mapeamento de Compliance

O `llm-inference-stack` mapeia suas funcionalidades técnicas diretamente para os controles exigidos por frameworks de mercado.

## Mapeamento Técnico

| Funcionalidade | Controle SOC 2 | Controle ISO 27001 | Status |
| :--- | :--- | :--- | :--- |
| RBAC Administrativo | CC6.1 | A.9.1.1 | Implemented |
| Audit Logging | CC7.1 | A.12.4.1 | Implemented |
| Release Gates | CC8.1 | A.12.1.2 | Implemented |
| Secret Scanning | CC7.1 | A.12.6.1 | Implemented |
| SBOM / Checksums | CC8.1 | A.15.1.1 | Implemented |
| Chaos Engineering | CC7.1 | A.17.1.1 | Implemented |
| Operational Readiness | CC7.1 | A.12.1.1 | Implemented |

## Governança
Cada controle possui um **Owner Role** responsável pela revisão periódica das evidências e pela manutenção da conformidade.

## Gaps Identificados
- **SOC 2 CC7.2**: Detecção de anomalias em tempo real via IA ainda está em modo advisory.
- **ISO A.14.2.1**: Segurança no desenvolvimento (Secure Coding) requer treinamento formal documentado.
