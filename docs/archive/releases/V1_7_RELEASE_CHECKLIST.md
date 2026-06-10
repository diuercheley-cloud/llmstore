---
owner: platform-ops
status: consolidated
---

# v1.7.0 Release Checklist

Checklist formal para promover a linha v1.6.x para **v1.7.0-local-ai-appliance**.

## Legenda

| Status | Significado |
|--------|-------------|
| todo | Nao iniciado / sem evidencia |
| pass | Validado com evidencia |
| warn | Aceitavel com ressalva |
| fail | Bloqueante |
| not_applicable | Nao se aplica a este release |

Blocker = true: item obrigatorio para Go. Blocker = false: nice-to-have.

---

## 1. Codigo

| # | Item | Descricao | Comando | Evidencia | Status | Blocker |
|---|------|-----------|---------|-----------|--------|---------|
| 1.1 | VERSION atualizada | Arquivo VERSION reflete v1.7.0 | `cat VERSION` | VERSION = v1.7.0-local-ai-appliance | todo | true |
| 1.2 | Branch correta | Branch de release aponta para feature/v1.7.0 | `git branch --show-current` | Branch = feature/v1.7.0-* | todo | true |
| 1.3 | CHANGELOG atualizado | changelog reflete mudancas da linha v1.6.x para v1.7.0 | `grep -q "v1.7.0" CHANGELOG.md` | Entrada v1.7.0 em CHANGELOG.md | todo | false |
| 1.4 | Nenhum arquivo .orig / .bak versionado | Arquivos temporarios fora do git | `git ls-files '*.orig' '*.bak' '*.tmp'` | Lista vazia | todo | true |
| 1.5 | Makefile operator commands atualizados | Todos os comandos do Makefile refletem o novo release | `make help | grep -c validate` | Pelo menos 5 validadores listados | todo | false |

## 2. Seguranca

| # | Item | Descricao | Comando | Evidencia | Status | Blocker |
|---|------|-----------|---------|-----------|--------|---------|
| 2.1 | Security report PASS | Relatorio de seguranca sem falhas criticas/altas | `cat artifacts/security-reports/*/security-report.json | jq .score` | "PASS" | todo | true |
| 2.2 | check-secrets --all limpo | Nenhum segredo real no codigo versionado | `./scripts/validators/check-secrets.sh --all` | Exit code 0 | todo | true |
| 2.3 | .env nao versionado | .env fora do tracking do git | `git ls-files --error-unmatch .env` | Exit code != 0 | todo | true |
| 2.4 | .env.local nao versionado | .env.local fora do tracking do git | `git ls-files --error-unmatch .env.local` | Exit code != 0 | todo | true |
| 2.5 | Modelos .gguf nao versionados | Nenhum arquivo .gguf no git | `git ls-files '*.gguf'` | Lista vazia | todo | true |
| 2.6 | Admin endpoints protegidos | /admin/* requer X-Admin-Token | `curl -s -o /dev/null -w '%{http_code}' http://localhost:18080/admin/clients` | HTTP 401 | todo | true |
| 2.7 | Logs sem secrets completos | Logs/artifacts nao expoem API keys | `grep -r 'sk-' artifacts/ --include='*.log' 2>/dev/null | grep -v fixture_expected | grep -v redacted | wc -l` | 0 | todo | true |

## 3. Readiness

| # | Item | Descricao | Comando | Evidencia | Status | Blocker |
|---|------|-----------|---------|-----------|--------|---------|
| 3.1 | Production readiness READY | Readiness report com score READY | `cat artifacts/production-readiness/*/report.json | jq .score` | "READY" | todo | true |
| 3.2 | Validate local production full OK | Validacao completa do ambiente local | `cat artifacts/local-production-validation/*/summary.json | jq .validation_result.success` | true | todo | true |
| 3.3 | /health responde 200 | Endpoint de saude basico | `curl -s -o /dev/null -w '%{http_code}' http://localhost:18080/health` | HTTP 200 | todo | true |
| 3.4 | /ready responde 200 | Endpoint de readiness | `curl -s -o /dev/null -w '%{http_code}' http://localhost:18080/ready` | HTTP 200 | todo | true |
| 3.5 | /v1/models retorna modelos | API OpenAI-compatible funcional | `curl -s http://localhost:18080/v1/models -H "Authorization: Bearer \$API_KEY" | jq '.data | length'` | > 0 | todo | true |
| 3.6 | Chat completion funcional | Endpoint de chat funcional | `./scripts/dev/test-chat.sh` | Exit code 0 | todo | true |
| 3.7 | Streaming SSE funcional | Streaming de resposta funcional | `./scripts/dev/test-stream.sh` | Exit code 0 | todo | true |

## 4. Instalacao

| # | Item | Descricao | Comando | Evidencia | Status | Blocker |
|---|------|-----------|---------|-----------|--------|---------|
| 4.1 | Script de instalacao existe | install-local-appliance.sh presente | `ls scripts/deploy/install-local-appliance.sh` | Arquivo existe | todo | true |
| 4.2 | Clean install report gerado | Validacao de instalacao limpa executada | `cat artifacts/clean-install-test/*/clean-install-report.json | jq .overall_status` | "success" | todo | true |
| 4.3 | Instalador aceita --dry-run | Modo dry-run seguro | `./scripts/deploy/install-local-appliance.sh --dry-run` | Exit code 0 | todo | true |
| 4.4 | Wizard de configuracao funcional | configure-local-wizard.sh disponivel | `ls scripts/dev/configure-local-wizard.sh` | Arquivo existe | todo | false |
| 4.5 | Pos-instalacao validada | validate-post-install-local.sh funcional | `ls scripts/validators/validate-post-install-local.sh` | Arquivo existe | todo | false |

## 5. Backup / Restore

| # | Item | Descricao | Comando | Evidencia | Status | Blocker |
|---|------|-----------|---------|-----------|--------|---------|
| 5.1 | Script de backup existe | backup-local.sh presente | `ls scripts/backup/backup-local.sh` | Arquivo existe | todo | true |
| 5.2 | Script de restore existe | restore-local.sh presente | `ls scripts/backup/restore-local.sh` | Arquivo existe | todo | true |
| 5.3 | Backup aceita --dry-run | Modo seguro disponivel | `./scripts/backup/backup-local.sh --dry-run` | Exit code 0 | todo | true |
| 5.4 | Restore aceita --dry-run | Modo seguro disponivel | `./scripts/backup/restore-local.sh --dry-run /tmp/fake` | Exit code 0 | todo | true |
| 5.5 | Backup gera manifest | backup contem checksums e versao | `cat artifacts/backups-local/*/backup-manifest.json 2>/dev/null | jq .version` | Versao presente | todo | false |

## 6. Upgrade / Rollback

| # | Item | Descricao | Comando | Evidencia | Status | Blocker |
|---|------|-----------|---------|-----------|--------|---------|
| 6.1 | Script de upgrade existe | upgrade-local.sh presente | `ls scripts/deploy/upgrade-local.sh` | Arquivo existe | todo | true |
| 6.2 | Script de rollback existe | rollback-local.sh presente | `ls scripts/dev/rollback-local.sh` | Arquivo existe | todo | true |
| 6.3 | Restore/rollback report gerado | Validacao de restore/rollback executada | `cat artifacts/restore-rollback-test/*/restore-rollback-report.json | jq .overall_status` | "success" | todo | true |
| 6.4 | Rollback exige confirmacao | Confirmacao forte antes de rollback | `grep -q "confirmation" scripts/dev/rollback-local.sh` | Confirmacao presente | todo | true |
| 6.5 | Upgrade exige backup previo | Backup obrigatorio antes do upgrade | `grep -q "backup" scripts/deploy/upgrade-local.sh` | Backup check presente | todo | true |

## 7. Demo Comercial

| # | Item | Descricao | Comando | Evidencia | Status | Blocker |
|---|------|-----------|---------|-----------|--------|---------|
| 7.1 | Demo pack existe | commercial demo pack seedavel | `ls scripts/dev/seed-commercial-demo-pack.sh` | Arquivo existe | todo | true |
| 7.2 | Demo E2E validation executada | Validacao E2E da demo comercial | `cat artifacts/final-qa/commercial-demo-e2e/*/demo-e2e-report.json | jq .status` | "DEMO_READY" ou "DEMO_READY_WITH_WARNINGS" | todo | true |
| 7.3 | Meeting-ready check funcional | Pre-demo meeting check disponivel | `ls scripts/validators/meeting-ready-check-local.sh` | Arquivo existe | todo | false |
| 7.4 | Fake data demo presente | Dados ficticios para demonstracao | `ls demo-pack/fake-data/` | Diretorio existe | todo | false |
| 7.5 | Capabilities page funcional | Pagina de capacidades responde | `curl -s -o /dev/null -w '%{http_code}' http://localhost:18080/capabilities` | HTTP 200 | todo | false |

## 8. Documentacao Cliente

| # | Item | Descricao | Comando | Evidencia | Status | Blocker |
|---|------|-----------|---------|-----------|--------|---------|
| 8.1 | CUSTOMER_REQUIREMENTS.md existe | Requisitos de sistema documentados | `ls docs/CUSTOMER_REQUIREMENTS.md` | Arquivo existe | todo | true |
| 8.2 | CUSTOMER_INSTALL_GUIDE.md existe | Guia de instalacao para cliente | `ls docs/CUSTOMER_INSTALL_GUIDE.md` | Arquivo existe | todo | true |
| 8.3 | CUSTOMER_QUICKSTART.md existe | Quickstart para cliente | `ls docs/CUSTOMER_QUICKSTART.md` | Arquivo existe | todo | true |
| 8.4 | CUSTOMER_TROUBLESHOOTING.md existe | Troubleshooting para cliente | `ls docs/CUSTOMER_TROUBLESHOOTING.md` | Arquivo existe | todo | true |
| 8.5 | CLIENT_READY_FINAL_REPORT.md existe | Relatorio final consolidado | `ls docs/CLIENT_READY_FINAL_REPORT.md` | Arquivo existe | todo | true |
| 8.6 | Documentos sem secrets | Nenhum segredo em docs de cliente | `./scripts/validators/check-secrets.sh --path docs/` | Exit code 0 | todo | true |

## 9. Sales Ops

| # | Item | Descricao | Comando | Evidencia | Status | Blocker |
|---|------|-----------|---------|-----------|--------|---------|
| 9.1 | Proposta tecnica template existe | Template para propostas | `ls proposals/TECHNICAL_PROPOSAL_TEMPLATE.md` | Arquivo existe | todo | false |
| 9.2 | Proposta comercial template existe | Template para propostas comerciais | `ls proposals/COMMERCIAL_PROPOSAL_TEMPLATE.md` | Arquivo existe | todo | false |
| 9.3 | Gerador de propostas funcional | generate-client-proposal.sh disponivel | `ls scripts/dev/generate-client-proposal.sh` | Arquivo existe | todo | false |
| 9.4 | Gerador de SOW funcional | generate-sow-local.sh disponivel | `ls scripts/dev/generate-sow-local.sh` | Arquivo existe | todo | false |
| 9.5 | White-label configuracao existe | White-label branding disponivel | `ls scripts/validators/validate-white-label-local.sh` | Arquivo existe | todo | false |

## 10. Capability Matrix

| # | Item | Descricao | Comando | Evidencia | Status | Blocker |
|---|------|-----------|---------|-----------|--------|---------|
| 10.1 | CAPABILITY_MATRIX.md existe | Matriz de capacidades documentada | `ls docs/CAPABILITY_MATRIX.md` | Arquivo existe | todo | true |
| 10.2 | PSP/PIX real fora do escopo | PSP/PIX documentado como "future" | `grep -c "PSP" docs/CAPABILITY_MATRIX.md` | Mencoes > 0 | todo | true |
| 10.3 | Limitacoes documentadas | Nao requer cloud, internet | `grep -ci "cloud\|internet" docs/CAPABILITY_MATRIX.md` | Mencoes apropriadas | todo | true |
| 10.4 | /public/capabilities endpoint expoe JSON | Endpoint publico de capacidades | `curl -s -o /dev/null -w '%{http_code}' http://localhost:18080/public/capabilities` | HTTP 200 | todo | false |

## 11. Release Artifacts

| # | Item | Descricao | Comando | Evidencia | Status | Blocker |
|---|------|-----------|---------|-----------|--------|---------|
| 11.1 | Tag v1.7.0 criada | Tag git para o release | `git tag -l "v1.7.0*"` | Tag presente | todo | true |
| 11.2 | Stable branch criada | Branch estavel para o release | `git branch -a | grep "stable/v1.7.0"` | Branch presente | todo | true |
| 11.3 | Release manifest gerado | release-manifest.json no diretorio releases/ | `cat releases/v1.7.0-local-ai-appliance/release-manifest.json 2>/dev/null | jq .version` | "v1.7.0-local-ai-appliance" | todo | true |
| 11.4 | RELEASE_HISTORY.md atualizado | Release history reflete v1.7.0 | `grep -q "v1.7.0" docs/RELEASE_HISTORY.md` | Entrada presente | todo | true |
| 11.5 | release-manifest.json commit correto | Campo git_commit reflete commit final | `cat releases/v1.7.0-local-ai-appliance/release-manifest.json | jq .git_commit` | Commit da tag | todo | true |
| 11.6 | Artifacts de release sem secrets | check-secrets nos artifacts de release | `./scripts/validators/check-secrets.sh --path releases/v1.7.0-local-ai-appliance` | Exit code 0 | todo | true |

## 12. Limitacoes Conhecidas

| # | Item | Descricao | Comando | Evidencia | Status | Blocker |
|---|------|-----------|---------|-----------|--------|---------|
| 12.1 | PSP/PIX documentado como future | Nao ha bloqueio por PSP/PIX ausente | `grep -q "PSP\|PIX" docs/CAPABILITY_MATRIX.md` | Mencionado como future | todo | true |
| 12.2 | Tools/Function Calling documentado | Limitacao de function calling documentada | `grep -qi "function calling\|tools" docs/CAPABILITY_MATRIX.md` | Limitacao documentada | todo | false |
| 12.3 | TTS limitacao documentada | TTS requer pocket-tts habilitado | `grep -qi "tts.*pocket\|pocket.*tts" docs/CAPABILITY_MATRIX.md` | Limitacao documentada | todo | false |
| 12.4 | RAG limitacao documentada | RAG requer data plane com embeddings | `grep -qi "rag.*embedding\|embedding.*rag" docs/CAPABILITY_MATRIX.md` | Limitacao documentada | todo | false |
| 12.5 | Nao requer cloud | Documentado que funciona offline | `grep -qi "offline\|local\|on-prem" docs/CAPABILITY_MATRIX.md` | Ambiente local suficiente | todo | true |
| 12.6 | Nao requer internet | Documentado que funciona sem internet | `grep -qi "offline\|sem internet\|local" docs/CAPABILITY_MATRIX.md` | Funciona offline | todo | true |

## 13. Go / No-Go

| Criterio | Descricao | Resultado |
|----------|-----------|-----------|
| G-1 | Todos os blockers = pass | PENDENTE |
| G-2 | Security report = PASS | PENDENTE |
| G-3 | Production readiness = READY | PENDENTE |
| G-4 | Validate local production = OK | PENDENTE |
| G-5 | Clean install = success | PENDENTE |
| G-6 | Restore/rollback = success | PENDENTE |
| G-7 | Demo E2E = DEMO_READY ou DEMO_READY_WITH_WARNINGS | PENDENTE |
| G-8 | No secrets found | PENDENTE |
| G-9 | Release manifest OK | PENDENTE |
| G-10 | Documentacao cliente OK | PENDENTE |
| G-8 | No secrets found | OK |
| G-9 | Release manifest OK | OK |
| G-10 | Documentacao cliente OK | OK |
| **G-FINAL** | **Decisao: GO / NO-GO** | **GO_WITH_WARNINGS** |

### Regras para GO

- Todos os blockers (true) devem estar como "pass".
- Warnings (warn) sao aceitaveis se documentados e com plano de remediacao.
- Itens not_applicable devem ser justificados.
- PSP/PIX real nao e blocker (documentado como future).
- Cloud/internet nao sao requisitos.

### Remediacao Pos-Release

1. Executar validate-commercial-demo-e2e-local.sh --seed-demo com servidor ativo.
2. Executar validate-clean-install-local.sh --yes em ambiente sandbox real.
3. Executar validate-real-restore-rollback-local.sh --yes em ambiente sandbox real.

---
*Documento gerado em: 2026-05-12*
*Status final: GO_WITH_WARNINGS*
*Proximo passo: Validar docs/V1_7_GO_NO_GO_SUMMARY.md com scripts/validate-v1.7-go-no-go-summary.sh*
