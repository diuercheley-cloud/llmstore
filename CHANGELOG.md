# Changelog

## [v1.6.4-customer-demo-pack] - 2026-05-11

### Added
- Demo pack comercial com 5 cenarios (clinica, juridico, suporte, educacao, provedor-api), planos e dados ficticios.
- Roteiro de apresentacao para cliente com scripts de 15/30/60 minutos e talk tracks prontos.
- Proposta tecnica Markdown/PDF geravel com `scripts/generate-proposal-pdf.sh`.
- Reset demo seguro com dry-run padrao, --yes obrigatorio e metadata demo=true.
- Dados ficticios realistas em `demo-pack/fake-data/` com validacao dedicada.
- Meeting Ready Check (`scripts/meeting-ready-check-local.sh`) com status MEETING_READY, READY_WITH_WARNINGS, NOT_READY.
- Pagina local /capabilities com recursos, status (GA/Beta/Future) e limitacoes explicitas (PSP, PIX, Tools/FC).
- Endpoint JSON `GET /public/capabilities` com versao, features, limitations, local_appliance_mode, sem secrets.
- Landing page atualizada com link para /capabilities.
- Scripts de validacao: validate-commercial-demo-pack, validate-client-presentation-docs, validate-fake-demo-data, validate-meeting-ready-check, validate-capabilities-page, validate-proposals-local, validate-reset-commercial-demo-pack.
- Testes dedicados para demo pack, apresentacao, propostas, meeting-ready, capabilities page e seguranca.

### Notes
- PSP real nao incluido — faturamento e manual.
- PIX real nao incluido — sem QR Code ou cobranca automatica.
- Tools/Function Calling parcial — depende do backend local.
- Dados demo marcados como ficticios/demo via metadata.
- Release preparada para bundle sem versionar secrets, `.env`/`.local`, modelos `.gguf`, uploads RAG ou artefatos brutos.

## [v1.6.3-readiness-cleanup] - 2026-05-11

### Added
- Correção de warnings do Production Readiness report com diagnóstico automatizado.
- Modelo de chat utilizável no `/v1/models` probe para validação de readiness.
- Probe chat/SSE robusto com capability opcional e fallback seguro.
- TTS readiness auth corrigido com validação de autenticação explícita.
- Rate limit probe seguro com cleanup e verificação de segurança.
- CORS local/appliance explícito com defaults seguros e probe de readiness.
- Production Readiness final READY com score de validação e security report PASS.
- Testes dedicados para readiness cleanup v1.6.3 e production readiness ready score.

### Notes
- Release preparada para bundle e validação local completa sem versionar secrets, `.env`/`.local`, modelos `.gguf`, uploads RAG ou artefatos brutos.

## [v1.6.2-installer-polish] - 2026-05-11

### Added
- Instalador local `install-local-appliance.sh` e wizard `configure-local-wizard.sh` para preparar appliances de cliente final com mensagens operacionais amigáveis.
- Checklist pré-demo/pré-cliente, documentação de instalação para cliente final e catálogo de erros operacionais sanitizados.
- Backup automático antes de upgrade, integração de rollback com backup de upgrade e validação completa pós-instalação.
- Scripts de validação local para instalador, wizard, checklist, documentação, erros operacionais, backup/upgrade e pós-instalação.
- Cobertura de testes dedicada para segurança, relatórios e fluxos operacionais da release `installer-polish`.

### Notes
- Release preparada para bundle e validação local completa sem versionar secrets, `.env`/`.local`, modelos `.gguf`, uploads RAG ou artefatos brutos.

## [v1.6.1-product-hardening] - 2026-05-10

### Added
- Makefile consolidado como entrypoint operacional para rotinas locais de produto e validação.
- System Control Center com cobertura de API, UI e sanitização de saídas administrativas.
- Hardening de migrations com validações de heads, safety checks de upgrade e documentação de operação.
- `LOCAL_APPLIANCE_MODE` com guards de release e validações específicas de segurança local.
- Isolamento multi-tenant reforçado para embeddings, responses, TTS, billing portal e export/delete.
- Proteções contra abuso com autenticação, limites, validação de payloads e isolamento por tenant.
- Matriz comercial de planos e gates de features refletidos em API, portal e pricing.
- Capability matrix e documentação de integrações com exemplos locais sem secrets.

### Notes
- Release preparada para validação local completa, incluindo relatórios de segurança, readiness e bundle sem artefatos proibidos versionados.

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
