# Platform Architectural Freeze Policy

Este documento estabelece as regras e diretrizes formais para a fase de congelamento arquitetural (Architectural Freeze) do `llm-inference-stack`, com o objetivo de estabilizar o core do sistema, evitar a expansão horizontal descontrolada e garantir a prontidão para conformidade (compliance readiness).

A base de referência para esta política é a tag/versão **`v1.9.7-compliance-readiness`**.

---

## 1. Escopo do Freeze

O congelamento arquitetural aplica-se a toda a estrutura do repositório, especificamente:
- A estrutura de diretórios do repositório (diretórios raiz).
- Os contextos delimitados (bounded contexts) sob `control_plane/app/services`.
- As rotas e controladores de API (routers) sob `control_plane/app/api`.
- Os modelos de dados ORM (classes declarativas SQLAlchemy) sob `control_plane/app/models`.
- A inclusão de novas flags de funcionalidade (feature flags) em `control_plane/app/core/config.py`.
- A introdução de novos endpoints HTTP sem classificação explícita de superfície.

---

## 2. Regras de Mudança

Durante a vigência do congelamento arquitetural, aplicam-se as seguintes regras para triagem de pull requests e commits:

### O que é Permitido (Allowed)
- **Correções de Bugs (Bugfixes)**: Correções de código que resolvam falhas e não alterem a assinatura de APIs públicas ou contratos de banco.
- **Melhorias de Performance**: Otimizações internas de algoritmos, queries e lógica de negócio existentes.
- **Refatorações de Código**: Limpeza de código, melhoria de legibilidade e manutenibilidade sem introdução de novas dependências arquiteturais.
- **Melhorias de Testes**: Adição de novos testes unitários, de integração ou de smoke-tests para cobrir lógica existente.

### O que é Bloqueado (Blocked)
- **Novos Diretórios Raiz**: Nenhuma pasta nova na raiz do projeto é permitida.
- **Novos Bounded Contexts**: Nenhuma pasta nova sob `control_plane/app/services` é permitida.
- **Novas APIs/Routers sem Aprovação**: Novas rotas de API adicionadas fora das pré-aprovadas são bloqueadas.
- **Novas Feature Flags sem Dono/Status**: Qualquer nova feature flag inserida no arquivo de configurações deve declarar obrigatoriamente um dono (`Owner: <dono>`) e um status (`Status: <status>`).
- **Novos Serviços sem Documentação**: Qualquer novo arquivo de serviço python sob `control_plane/app/services` deve conter docstrings formais ou tag de dono.
- **Novos Modelos ORM sem Migration e Dono**: Novos modelos declarativos do SQLAlchemy sem migration Alembic correspondente ou sem tag de dono são sumariamente bloqueados.
- **Novos Endpoints sem Classificação**: Qualquer nova rota FastAPI (`@router.get`, `@router.post`, etc.) inserida deve pertencer a um roteador ou arquivo com classificação de superfície explícita (`admin`, `client`, `portal`, `public`).

---

## 3. Processo de Exceção e Aprovação

Caso seja estritamente necessário introduzir uma mudança arquitetural bloqueada, o seguinte fluxo deve ser seguido:

1. **Architecture Decision Record (ADR)**: O proponente deve criar um ADR descrevendo a necessidade, alternativas consideradas e impacto da mudança.
2. **Atualização de Regras**: O caminho, classe ou flag deve ser adicionado à lista `approved_exceptions` no arquivo `config/platform-freeze-rules.json`.
3. **Revisão e Aprovação**: O pull request deve passar pela revisão obrigatória e aprovação formal da equipe de Arquitetura.
