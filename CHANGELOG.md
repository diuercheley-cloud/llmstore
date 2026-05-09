# Changelog

## [v1.5.6-runtime-hardening] - 2026-05-09

### Added
- Runtime health e admin deep health com sanitização de informações sensíveis.
- Governança de TTS com quotas, billing local, client portal e dashboard administrativo.
- Benchmark real por modelo com exposição segura via Admin API e documentação operacional.
- Fluxo local de upgrade/rollback com smoke test pós-upgrade e validações de segurança.
- Dashboard e APIs de readiness/security com cobertura de testes e validações locais.

### Notes
- `/v1/embeddings` e `/v1/responses` permanecem fora desta release enquanto não estiverem prontos.

## [v1.6.0-beta.1] - 2026-05-09

### Added
- OpenAI-compatible `/v1/responses` endpoint as a simplified compatibility layer.
- Refactored chat completions pipeline to support multiple entry points.
- Support for `instructions` and `input` (string or array) in `/v1/responses`.
- Simplified `/v1/responses` output contract with `created_at`, `status`, `output`, `output_text`, `usage`, and metadata passthrough.
- Compatibility headers for model routing and fallback: `X-Requested-Model`, `X-Resolved-Model`, `X-Backend-Name`, `X-Fallback-Used`.
- Explicit `501` responses for unsupported `tools`, `tool_choice`, and `stream` in `/v1/responses`.
- Automated tests and examples for the new endpoint.
- Validation script `scripts/validate-responses-api-local.sh`.
- OpenAI-compatible `/v1/embeddings` endpoint.
- Deterministic mock embeddings backend for local testing and integration.
- Embeddings quota management and usage tracking (requests and tokens).
- New embedding fields in `BillingPlan`, `QuotaCounter`, and `UsageRecord`.
- Example scripts for embeddings in CURL, Python, and Node.js.
- Validation script `scripts/validate-embeddings-local.sh`.
- Comprehensive test suite for embeddings.
- New documentation: `docs/OPENAI_COMPATIBILITY.md`.

## [v1.5.5-security-artifacts-clean] - 2026-05-09

### Added
- artifact secret diagnosis
- source redaction for generated artifacts
- safe cleanup/redaction for ignored artifacts
- stronger release artifacts validation
- improved security-report scoring for redacted ignored artifacts
- guarantee summaries/releases do not carry test tokens

## [v1.5.4-security-cleanup] - 2026-05-08

### Added
- security report cleanup workflow
- release artifacts security validation
- permissions validation/fix scripts
- `.pem`/`.key` policy
- `.gitignore` hardening
- safe fixture classification in check-secrets/security-report
- final security cleanup validator

## [v1.5.2-local-ops] - 2026-05-08

### Added
- production readiness report
- security report local
- retention policy local
- tenant export seguro
- tenant delete seguro
- model benchmark
- release bundle seguro
- first-run local

## [v1.5.1-local-production] - 2026-05-08

### Fixed
- fixed release metadata version source
- aligned release manifest, summary.json and summary.md
- added validate-release-metadata.sh
- added regression test for release metadata consistency

## [v1.4.4-local-demo] - 2026-05-08

### Added
- Modo demo local completo rodando em `http://localhost:18080`.
- Cliente demo pré-configurado para fluxos locais de produto.
- API key demo segura gerada em `.local/`, sem expor a chave completa no repositório.
- Documentos RAG demo para testes rápidos de ingestão e consulta.
- Portal demo para experiência do cliente local.
- Dashboard demo para administração local.
- Exemplos de uso em curl, Python e Node.js.
- Script `demo-full-local.sh` para executar a jornada demo completa.
- Landing page local melhorada para onboarding do demo.
- Documentação de demo em `docs/LOCAL_DEMO_GUIDE.md`, `docs/LOCAL_DEMO_FAQ.md` e materiais relacionados.
- Escopo local preservado sem PSP real ou PIX real.

### Fixed
- Robustez no script de demonstração ao lidar com portas de controle de plano.

## [v1.4.3-local-hardening] - 2026-05-07

### Added
- Logging padronizado dos validadores para melhor rastreabilidade.
- Arquivos summary.md e summary.json melhorados com detalhes da validação.
- Release manifest automático em cada execução de release.
- Runbook local detalhado em docs/LOCAL_PRODUCTION_RUNBOOK.md.
- Check de secrets automático para prevenir vazamento de credenciais.
- Limpeza segura de dados RAG locais com script dedicado.

### Changed
- Processo de DR e restore revalidado para ambiente local.
- Scripts de validação agora suportam modo localhost como principal.
- Reforço da segurança no manuseio de dados locais.
