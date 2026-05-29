---
owner: platform-ops
status: consolidated
---

# OPA/Rego Policy Runtime (Phase 61)

## Visão Geral
A Fase 61 introduz um motor de avaliação de políticas declarativo compatível com Rego/OPA (Open Policy Agent), projetado para ser executado de forma "embedded" (embutida) dentro do Control Plane do LLM Inference Stack.

Este motor substitui gradualmente as validações baseadas em heurísticas e strings por um modelo estruturado, mantendo a compatibilidade offline-first, modo soberano e execução isolada, **sem depender de serviços SaaS externos ou binários não-nativos na imagem inicial**.

## Componentes

### 1. Modelos (Database)
- **CommercialPolicyRuntimeBundle**: Armazena hashes de bundles de políticas assinados, garantindo imutabilidade e versionamento seguro. Suporta fallback de tenant_id para global.
- **CommercialPolicyEvaluation**: Histórico imutável de avaliações contendo o `decision_trace` e o `enforcement_result` para auditoria.
- **CommercialPolicySimulation**: Permite execuções `dry_run` onde a política é testada com payloads reais e o diff é gerado.
- **CommercialPolicyDecisionLog**: Detalha regras acionadas, ações tomadas e o contexto.
- **CommercialPolicyViolation**: Registra falhas, severidade e sugere dicas de remediação.

### 2. Runtime de Policy (Services)
- `RegoRuntime`: Um emulador/wrapper do motor de Rego. Avalia determinísticamente os payloads baseados nas regras carregadas (mock local para garantir execução isolada).
- `PolicyEvaluator`: Orquestra todo o fluxo. Resolve qual bundle utilizar (herdando do tenant e caindo para o global), inicializa a trace de explainability e executa a política em modos variados (`enforce`, `dry_run`, `advisory`, `sovereign_strict`).
- `PolicyTraceBuilder`: Constrói a cadeia de inferência de decisão, listando quais regras deram "match", quais falharam e qual o caminho de enforcement até o veredito final.

### 3. API
Endpoints de gerência:
- `POST /admin/policy/runtime/evaluate`: Avalia payload de forma síncrona.
- `POST /admin/policy/runtime/simulate`: Registra execução dry_run para análise de diff.
- `GET /admin/policy/runtime/trace/{id}`: Resgata o trace de uma avaliação passada.
- `GET /admin/policy/runtime/violations`: Lista as infrações ocorridas.
- `GET /portal/policy/evaluations`: Expõe para os clientes seu próprio histórico de políticas aplicadas.

## Modos de Operação
- **Enforce**: Avalia e aplica a decisão (deny = blocked).
- **Advisory**: Avalia, se houver violações elas são transformadas em `warn` (permitindo a continuidade do fluxo, útil para transição suave de políticas).
- **Dry_Run**: Apenas simula e registra em DB; nunca bloqueia e não é contabilizado como tráfego em produção.

## Segurança e Imutabilidade
Todos os bundles são verificados por hash (SHA256). Avaliações incluem qual hash exato de runtime as avaliou. Traces não incluem PII sensível dos inputs, pois o contexto de avaliação isola as chaves criptográficas do workflow.
