---
owner: platform-ops
status: consolidated
---

# Supported Surface Area Policy

Este documento define e classifica formalmente as capacidades do `llm-inference-stack` de acordo com suporte real, maturidade e evidência operacional.

## Categorias de Maturidade (Support Levels)

A stack classifica cada capacidade em uma das seguintes categorias oficiais:

1. **supported**: Pronta para produção, com cobertura de testes robusta e suporte ativo.
2. **beta**: Funcionalidade próxima da estabilidade final, disponível para pilotos e validação em ambientes controlados.
3. **experimental**: Funcionalidade em desenvolvimento ou avaliação inicial. Pode sofrer alterações que quebram compatibilidade.
4. **advisory**: Funcionalidades de segurança ou governança que operam apenas em modo informativo (dry-run/recomendação) por padrão.
5. **deprecated**: Capacidade marcada para remoção em versões futuras; substitutos recomendados devem ser usados.
6. **internal**: Infraestrutura interna de suporte da engenharia (ex: pipelines de CI/CD), sem visibilidade direta para operadores.
7. **non-production**: Existe código, contrato ou validação parcial, mas a evidência atual ainda não sustenta claim production.

---

## Matriz de Classificação de Recursos

Abaixo estão listadas as áreas que exigem maior clareza nesta release:

| Recurso / Área | Categoria | Owner | Descrição / Limitações |
|----------------|-----------|-------|------------------------|
| **OpenAI-compatible API** | `supported` | Core Team | Interface HTTP padrão para inferência. Cobertura completa de `/v1/chat/completions`. |
| **Admin RBAC** | `supported` | Security Team | Controle de acesso baseado em papéis configurado estaticamente via arquivos de regras. |
| **Billing** | `supported` | Billing Team | Controle financeiro com faturamento manual e suspensão de contas. |
| **RAG** | `supported` | RAG Team | Ingestão local de documentos e busca semântica offline. |
| **TTS** | `supported` | Audio Team | Síntese de voz local offline via pocket-tts. |
| **Multi-provider routing** | `supported` | Core Team | Roteamento dinâmico entre backends locais e provedores em nuvem. |
| **Hot swap GGUF** | `supported` | Model Team | Gerenciamento de modelos locais e atualização de backends em tempo real. |
| **Kubernetes** | `non-production` | Cloud Team | Existe superfície opcional, mas não entra como core suportado nesta linha. |
| **Distributed runtime** | `beta` | Cloud Team | Registro de nós, heartbeat, placement, lease e failover existem; ainda requer E2E real e operação validada para claim production. |
| **GPU orchestration** | `non-production` | Cloud Team | Continua majoritariamente advisory. |
| **Capability catalog / plugin supply chain** | `beta` | Product Team | Catálogo, checksum e assinatura existem, mas a esteira ainda é operator-only e draft-first. |
| **Managed control-plane** | `beta` | Cloud Team | Operacional apenas para metadados sanitizados; não é plano de dados distribuído. |
| **Multi-cluster** | `beta` | Cloud Team | Administração e status existem; produção depende de gates reais e boundary checks. |
| **CI/CD** | `internal` | Infra Team | Pipelines de teste, build e validação automatizados. |
| **Chaos engineering** | `experimental` | QA Team | Injeção de latência e queda simulada de provedores em testes. |
| **Compliance readiness** | `beta` | Compliance Team | Coleta de evidências e frameworks de auditoria SOC 2 / ISO 27001. |
| **PKI** | `advisory` | Security Team | Assinatura e verificação de chaves locais sem cadeia de confiança externa. |
| **Attestation** | `advisory` | Security Team | Validação de assinaturas de hardware em modo informativo. |
| **Hardware trust** | `advisory` | Security Team | Armazenamento seguro de chaves validado apenas localmente. |

---

## Diretrizes de Governança e Operação

### 1. Regras de Exibição no README
O `README.md` principal do repositório deve listar apenas capacidades classificadas como **supported**, **production_optional** ou **beta** como recursos principais. Qualquer menção a capacidades **experimental**, **advisory** ou **non-production** deve vir obrigatoriamente acompanhada de um aviso claro de limitação.

### 2. Documentação de Conformidade (Compliance Docs)
Documentos de conformidade, incluindo prontidão de segurança (SOC 2, ISO 27001, etc.), **nunca** devem retratar recursos `advisory`, `experimental` ou `non-production` como controles certificados ou obrigatoriamente aplicados. Eles devem ser descritos estritamente como controles opt-in, consultivos ou ainda em maturação.

### 3. Barreira de Liberação (Release Gate)
A esteira de integração contínua (CI) e a barreira de liberação (`release-gate`) falharão automaticamente se detectarem novos endpoints, routers ou feature flags sem classificação em `config/supported-surface.yaml`, `config/api-surface.yaml` e `config/feature-flags.yaml`.
