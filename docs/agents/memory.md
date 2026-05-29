---
owner: platform-ops
status: consolidated
---

# Agent Memory Layer

A Camada de Memória para Agentes permite a persistência de informações entre diferentes execuções, respeitando rigorosamente o isolamento multi-tenant e políticas de governança de dados.

## Conceitos

- **Memory Item**: Uma unidade individual de informação armazenada.
- **Memory Type**: Categorização da memória (ex: `short_term`, `long_term`, `episodic`).
- **Memory Policy**: Define regras de retenção, redação e criptografia para cada tenant e agente.
- **Provenance**: Rastreabilidade da origem da memória (ex: qual `run_id` gerou a informação).

## Configuração

- `AGENT_MEMORY_ENABLED`: Habilita a funcionalidade de memória (padrão `false`).
- `AGENT_LONG_TERM_MEMORY_ENABLED`: Habilita persistência de longo prazo (padrão `false`).
- `AGENT_MEMORY_WRITE_ENABLED`: Permite que agentes escrevam na memória durante execuções.
- `AGENT_MEMORY_EXPORT_ENABLED`: Permite a exportação de dados de memória por inquilino.

## Tipos de Memória

| Tipo | Descrição | Uso Típico |
|------|-----------|------------|
| `short_term` | Memória de curto prazo, volátil. | Contexto imediato da conversa. |
| `long_term` | Persistência duradoura. | Conhecimento acumulado sobre o usuário/domínio. |
| `episodic` | Baseada em eventos específicos. | Recordação de interações passadas completas. |
| `semantic` | Fatos e conceitos. | Base de conhecimento extraída de documentos. |
| `preference` | Preferências do usuário. | Configurações e estilos de resposta desejados. |
| `operational` | Logs de execução técnica. | Auditoria de passos internos complexos. |

## Segurança e Isolamento

- **Tenant Boundary**: Memórias nunca cruzam fronteiras entre inquilinos. Consultas são filtradas obrigatoriamente por `tenant_id`.
- **Redaction**: Informações sensíveis (como e-mails ou padrões de secrets) são mascaradas antes da persistência se a política de redação estiver ativa.
- **Secret Blocking**: O sistema bloqueia a gravação de conteúdos que pareçam conter chaves de API ou senhas.
- **Access Logging**: Toda leitura, escrita, deleção ou exportação gera um `AgentMemoryAccessEvent`.

## Retenção

Toda memória deve ter um campo `retention_until`. Após esta data, os itens são elegíveis para deleção automática por jobs de limpeza agendados.
