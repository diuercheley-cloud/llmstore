---
owner: platform-ops
status: consolidated
---

# Catálogo e Versionamento Agentic

O LLM Inference Stack implementa um sistema de catálogo centralizado e versionamento explícito para todos os componentes do ecossistema agentic. Isso garante reprodutibilidade, auditabilidade e capacidade de recuperação rápida (rollback).

## Componentes Suportados

Os seguintes tipos de itens são gerenciados pelo catálogo:

-   **agent**: Definições completas de agentes.
-   **tool**: Esquemas e configurações de ferramentas.
-   **prompt_baseline**: Prompts de sistema e templates base.
-   **eval_dataset**: Conjuntos de dados para teste e avaliação.
-   **policy**: Regras de governança e segurança.
-   **memory_policy**: Configurações de retenção e acesso à memória.
-   **planner**: Estratégias de planejamento de tarefas.

## Versionamento e Checksums

Cada vez que um item é registrado ou atualizado, uma nova entrada em `agent_catalog_versions` é criada.

-   **Version**: String de versão (ex: `1.0.2`).
-   **Checksum**: Hash SHA-256 gerado automaticamente a partir da configuração JSON do item. Isso garante que a versão é imutável; qualquer alteração no conteúdo exige uma nova versão ou resultará em um checksum diferente.

## Promoção para Produção (Promotion Gates)

Itens recém-criados entram no estado `draft`. Para que um item seja utilizado em ambiente produtivo, ele deve passar pelo processo de promoção:

1.  **Registro**: Nova versão é salva.
2.  **Validação**: Testes automatizados e avaliações (Evals) são executados contra a versão.
3.  **Promoção**: O operador executa o comando de promoção, movendo o status do item para `production` e marcando a data de `promoted_at`.

## Rollback (Reversão)

Em caso de incidentes causados por uma nova versão, o operador pode disparar um rollback imediato para qualquer versão anterior estável.

O processo de rollback:
1.  Identifica a versão de destino estável.
2.  Cria um registro em `agent_catalog_rollbacks` com o motivo e autor.
3.  Atualiza o ponteiro de produção do item para a versão estável anterior.
4.  Gera um evento de auditoria global.

## API de Administração

-   `GET /admin/agents/catalog`: Lista itens do catálogo.
-   `GET /admin/agents/catalog/{id}/versions`: Histórico de versões de um item.
-   `POST /admin/agents/catalog/{id}/promote`: Promove uma versão específica.
-   `POST /admin/agents/catalog/{id}/rollback`: Reverte para uma versão anterior.
