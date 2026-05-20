# Supported Surface Area Policy

Este documento define e classifica formalmente todas as capacidades e recursos do `llm-inference-stack` de acordo com o seu nível de suporte, maturidade e estabilidade.

## Categorias de Maturidade (Support Levels)

A stack classifica cada capacidade em uma das seguintes categorias oficiais:

1. **supported**: Pronta para produção, com cobertura de testes robusta e suporte ativo.
2. **beta**: Funcionalidade próxima da estabilidade final, disponível para pilotos e validação em ambientes controlados.
3. **experimental**: Funcionalidade em desenvolvimento ou avaliação inicial. Pode sofrer alterações que quebram compatibilidade.
4. **advisory**: Funcionalidades de segurança ou governança que operam apenas em modo informativo (dry-run/recomendação) por padrão.
5. **deprecated**: Capacidade marcada para remoção em versões futuras; substitutos recomendados devem ser usados.
6. **internal**: Infraestrutura interna de suporte da engenharia (ex: pipelines de CI/CD), sem visibilidade direta para operadores.
7. **placeholder**: Estruturas mockadas ou apenas de validação sem execução real ou efeitos práticos na plataforma.

---

## Matriz de Classificação de Recursos

Abaixo estão listadas todas as 19 áreas fundamentais da plataforma com seus respectivos níveis de classificação:

| Recurso / Área | Categoria | Owner | Descrição / Limitações |
|----------------|-----------|-------|------------------------|
| **OpenAI-compatible API** | `supported` | Core Team | Interface HTTP padrão para inferência. Cobertura completa de `/v1/chat/completions`. |
| **Admin RBAC** | `supported` | Security Team | Controle de acesso baseado em papéis configurado estaticamente via arquivos de regras. |
| **Billing** | `supported` | Billing Team | Controle financeiro com faturamento manual e suspensão de contas. |
| **RAG** | `supported` | RAG Team | Ingestão local de documentos e busca semântica offline. |
| **TTS** | `supported` | Audio Team | Síntese de voz local offline via pocket-tts. |
| **Multi-provider routing** | `supported` | Core Team | Roteamento dinâmico entre backends locais e provedores em nuvem. |
| **Hot swap GGUF** | `supported` | Model Team | Gerenciamento de modelos locais e atualização de backends em tempo real. |
| **Kubernetes** | `placeholder` | Cloud Team | Orquestração mockada. Sem implantação física em clusters Kubernetes por padrão. |
| **Distributed runtime** | `placeholder` | Cloud Team | Comunicação de malha e controle distribuído simulados. |
| **GPU orchestration** | `placeholder` | Cloud Team | Escalonamento e alocação de GPUs em modo de recomendação apenas. |
| **Marketplace** | `placeholder` | Product Team | Registro e carregamento de plugins mockados sem mercado de distribuição ativo. |
| **Managed control-plane** | `placeholder` | Cloud Team | Troca de metadados restrita e estritamente de validação. |
| **Multi-cluster** | `placeholder` | Cloud Team | Simulação de federação de clusters sem encaminhamento físico de tráfego. |
| **CI/CD** | `internal` | Infra Team | Pipelines de teste, build e validação automatizados. |
| **Chaos engineering** | `experimental` | QA Team | Injeção de latência e queda simulada de provedores em testes. |
| **Compliance readiness** | `beta` | Compliance Team | Coleta de evidências e frameworks de auditoria SOC 2 / ISO 27001. |
| **PKI** | `advisory` | Security Team | Assinatura e verificação de chaves locais sem cadeia de confiança externa. |
| **Attestation** | `advisory` | Security Team | Validação de assinaturas de hardware em modo informativo. |
| **Hardware trust** | `advisory` | Security Team | Armazenamento seguro de chaves validado apenas localmente. |

---

## Diretrizes de Governança e Operação

### 1. Regras de Exibição no README
O `README.md` principal do repositório deve listar apenas capacidades classificadas como **supported** ou **beta** como recursos principais. Qualquer menção a capacidades **experimental**, **advisory** ou **placeholder** deve vir obrigatoriamente acompanhada de um aviso claro de limitação.

### 2. Documentação de Conformidade (Compliance Docs)
Documentos de conformidade, incluindo prontidão de segurança (SOC 2, ISO 27001, etc.), **nunca** devem retratar recursos de nível `advisory` ou `placeholder` como controles certificados (certified) ou aplicados obrigatoriamente (enforced). Eles devem ser descritos estritamente como ferramentas consultivas ou informativas de apoio.

### 3. Barreira de Liberação (Release Gate)
A esteira de integração contínua (CI) e a barreira de liberação (`release-gate`) falharão automaticamente se detectarem novos endpoints, routers ou feature flags que não possuam sua respectiva classificação mapeada em `config/supported-surface.yaml`.
