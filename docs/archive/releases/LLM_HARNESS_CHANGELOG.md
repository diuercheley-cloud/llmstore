# LLM Harness Changelog

## Release Target

- **Versão alvo**: `vX.Y.Z-llm-harness-production-core`
- **Status**: Draft para promoção a Production Core
- **Escopo**: `scripts/llm_harness/`, `tests/integration/llm_harness/`, `scripts/validators/validate-llm-harness.sh`

## Mudanças Registradas

### 1. Modularização do harness

O LLM Harness foi consolidado como pacote modular em `scripts/llm_harness/`, com separação explícita de responsabilidades:

- `agent_client.py`: facade de execução do agente
- `providers.py`: registry e implementações de providers
- `sandbox.py`: isolamento de execução e cleanup
- `health.py`: health checks locais, provider, Docker e workspace
- `policy.py`: policy engine para shell, arquivos e patch
- `reporter.py`, `sanitizer.py`, `_logging.py`: observabilidade, relatórios e redaction
- `tools/`: ferramentas isoladas para arquivos, git, shell e testes

Impacto: redução de acoplamento, validação mais direcionada e promoção mais rastreável por componente.

### 2. AgentClient real

O `AgentClient` deixou de ser apenas um ponto de stub implícito e passou a atuar como facade real sobre providers registrados via `create_code_agent(...)`.

- Encaminha `chat_completion(...)`
- Expõe `health_check()`
- Reaproveita `get_agent_config()` e `list_agents()` quando suportados
- Preserva sanitização de headers/logs por provider

Impacto: o loop principal passa a depender de integração real com provider, não de fallback oculto em produção.

### 3. Sandbox Docker com cleanup garantido

O sandbox Docker foi endurecido com governança explícita de ciclo de vida:

- registro em `atexit`
- signal handlers para `SIGINT` e `SIGTERM`
- cleanup síncrono com `docker rm -f`
- rastreamento de containers ativos por execução
- `--network none`, limites de memória, CPU e PIDs

Impacto: redução de risco de orphan containers, vazamento de recursos e bypass de rede.

### 4. Structured logging

Foi adicionado logging estruturado em JSON com redaction automática:

- handler dedicado em `_logging.py`
- campos de correlação: `trace_id`, `task_id`, `agent_id`, `step_index`
- sanitização de mensagens antes de emissão
- fallback defensivo em caso de erro de serialização

Impacto: melhora de auditabilidade, troubleshooting e integração com pipelines de observabilidade.

### 5. Health checks operacionais

O harness agora possui checagens de saúde reutilizáveis para:

- ambiente local (`git`, `pytest`, `venv`)
- provider remoto
- disponibilidade de Docker
- existência, escrita e espaço livre no workspace

Impacto: detecção antecipada de falhas de ambiente antes de executar ciclos de código ou release.

### 6. Providers suportados

O registry atual confirma suporte a:

- `stub`
- `openai-compatible`
- `local-openai-compatible`
- `anthropic`
- `google`
- `control-plane`

Impacto: matriz de execução mais explícita, com validação por provider e base mais segura para promoção.

### 7. Security hardening

O endurecimento de segurança confirmado no código inclui:

- allowlist de comandos shell
- bloqueio de operadores perigosos e padrões proibidos
- restrição de leitura/escrita em caminhos sensíveis
- bloqueio de patches sobre arquivos críticos
- sanitização de segredos em logs, relatórios e mensagens de erro
- falha explícita em configuração inválida

Impacto: menor superfície para command injection, path traversal, exfiltração de segredos e mudanças inseguras.

### 8. Expansão da suíte de testes

A superfície atual de validação do harness coleta **164 testes** em `tests/integration/llm_harness/`, superando o marco solicitado de **142+**.

Cobertura observável inclui:

- client e providers
- sandbox e cleanup
- CLI e coding loop
- health e policy
- reporter e sanitização
- provider matrix
- smoke/e2e do modo code

### 9. Script de validação dedicado

O fluxo de validação do harness foi formalizado em `./scripts/validators/validate-llm-harness.sh`.

O script executa:

- checagem de pré-requisitos da `.venv`
- verificação de `pyproject.toml`
- validação de dependência obrigatória (`httpx`)
- `py_compile`
- `ruff`
- `mypy`
- correção de imports via `scripts/dev/fix_imports.py`
- `pytest tests/integration/llm_harness/`
- `cli health --local-only`
- `cli security --check-only`

Impacto: um único entrypoint reproduzível para validação local e gate de release.

## Evidências de Promoção

- Documento de promoção: `docs/releases/LLM_HARNESS_PRODUCTION_CORE.md`
- Gate formal: `docs/releases/LLM_HARNESS_RELEASE_GATE.md`
- Validação operacional: `./scripts/validators/validate-llm-harness.sh`
- Checagem de compliance do core: `scripts/validators/check-llm-harness-production-core.py`

## Itens Ainda Não Resolvidos por Este Changelog

- definição do número final da versão de release
- evidência anexada de execução do gate completo em ambiente de release
- decisão final de enablement padrão fora de modo experimental/candidate
