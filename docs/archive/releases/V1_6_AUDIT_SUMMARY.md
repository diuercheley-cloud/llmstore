---
owner: platform-ops
status: consolidated
---

# Auditoria da Linha v1.6.x — Summary

**Documento versionavel de auditoria da release line v1.6.x.**
Gerado automaticamente pelo script `scripts/validators/audit-v1.6-release-line.sh`.

## Tabela de Versoes v1.6.x

| Versao | Objetivo | Tag | Stable Branch | Manifest Status | Seguranca | Validacao | Observacoes |
|--------|----------|-----|---------------|-----------------|-----------|-----------|-------------|
| v1.6.0-openai-compat | OpenAI-compatible responses e embeddings APIs | `v1.6.0-openai-compat` | `stable/v1.6.0-openai-compat` | AUSENTE — sem diretorio releases/ | N/A | N/A | Stable branch avancada para commit v1.6.1; sem release dir |
| v1.6.1-openai-compat | Ajuste na versao e correcoes na API (tag obsoleta) | `v1.6.1-openai-compat` | NENHUMA | AUSENTE — sem diretorio releases/ | N/A | N/A | Tag obsoleta; substituida por v1.6.1-product-hardening |
| v1.6.1-product-hardening | Makefile, system control center, migrations, multi-tenant | `v1.6.1-product-hardening` | `stable/v1.6.1-product-hardening` | OK — 5/5 arquivos | PASS | PASS | Consistente |
| v1.6.2-installer-polish | Instalador local, wizard, backup/upgrade | `v1.6.2-installer-polish` | `stable/v1.6.2-installer-polish` | OK — 5/5 arquivos | PASS | PASS | Consistente |
| v1.6.3-readiness-cleanup | Readiness final, probe chat/SSE/TTS/CORS | `v1.6.3-readiness-cleanup` | `stable/v1.6.3-readiness-cleanup` | OK — 5/5 arquivos | PASS | PASS | Consistente |
| v1.6.4-customer-demo-pack | Demo pack comercial, 5 cenarios, capabilities | `v1.6.4-customer-demo-pack` | `stable/v1.6.4-customer-demo-pack` | INCOMPLETO — faltam summary.json e summary.md | PASS | INCOMPLETO | Summary ausente impede validacao completa |
| v1.6.5-sales-ops | CRM, propostas, orcamentos, contratos, white-label | `v1.6.5-sales-ops` | `stable/v1.6.5-sales-ops` | INCONSISTENTE — manifest aponta commit errado (v1.6.4) | PASS | INCONSISTENTE | release-manifest.json contem git_commit da versao anterior |
| v1.6.6-repo-cleanup | Consolidacao layout, padronizacao shell, historico | `v1.6.6-repo-cleanup` | `stable/v1.6.6-repo-cleanup` | INCONSISTENTE — manifest aponta commit errado (v1.6.5) | PASS | INCONSISTENTE | release-manifest.json contem git_commit da versao anterior |

## Resumo de Inconsistencias

| Categoria | Quantidade | Detalhes |
|-----------|------------|----------|
| Release dir ausente | 2 | v1.6.0-openai-compat, v1.6.1-openai-compat |
| Arquivos ausentes no release dir | 2 | v1.6.4-customer-demo-pack: summary.json, summary.md |
| Tag/Stable branch divergentes | 1 | v1.6.0-openai-compat |
| release-manifest.json commit errado | 2 | v1.6.5-sales-ops, v1.6.6-repo-cleanup |
| Tags obsoletas sem documentacao | 1 | v1.6.1-openai-compat |
| .tar.gz versionado | 0 | Nenhum encontrado |
| Secrets em artifacts | 0 | Nenhum encontrado |
| CHANGELOG incompleto | 1 | v1.6.0 listado como v1.6.0-beta.1 |

## Riscos Pendentes

1. **v1.6.0-openai-compat sem release dir**: Nao ha diretorio `releases/v1.6.0-openai-compat` com manifests. A stable branch tambem esta avancada para o commit errado.
2. **v1.6.4-customer-demo-pack sem summary**: Faltam `summary.json` e `summary.md`. Sem esses arquivos nao e possivel validar os metadados daquela release (testes, scripts, versao).
3. **v1.6.5 e v1.6.6 com commit errado no manifest**: O campo `git_commit` no `release-manifest.json` aponta para o commit da versao anterior, indicando que `release-local-production.sh` foi executado antes do merge final na branch de versao. Isso compromete a rastreabilidade.
4. **v1.6.0-openai-compat stable branch avancada**: `stable/v1.6.0-openai-compat` esta no commit `v1.6.1-openai-compat` (`e485ec6`), nao no commit da tag (`1363f44`). Isso significa que a branch estavel inclui mudancas que nao faziam parte daquela versao.
5. **Tags v1.6.1 duplicadas**: Existem `v1.6.1-openai-compat` e `v1.6.1-product-hardening`. A primeira parece ter sido substituida, mas nao ha documentacao formal de deprecacao.

## Recomendacao para v1.7.0

1. **Corrigir manifests**: Atualizar `release-manifest.json` de v1.6.5 e v1.6.6 para refletirem os commits corretos.
2. **Completar v1.6.4**: Gerar `summary.json` e `summary.md` para v1.6.4-customer-demo-pack executando a pipeline de validacao naquele commit.
3. **Documentar deprecacao**: Adicionar entrada no CHANGELOG e/ou RELEASE_HISTORY sobre a tag obsoleta `v1.6.1-openai-compat`.
4. **Alinhar stable/v1.6.0-openai-compat**: Mover a stable branch para o commit correto da tag, ou documentar a deciso de mante-la avancada.
5. **CI hardening**: Adicionar validacao que impede `release-manifest.json` com `git_commit` diferente do commit onde o script de release foi executado.
6. **Formato uniforme**: Decidir entre campos `commit` (formato antigo, usado em v1.6.4) e `git_commit` (formato atual) e migrar todas as releases para o mesmo formato.
7. **v1.6.0 release dir**: Avaliar se e necessario criar o diretorio `releases/v1.6.0-openai-compat` para completude do historico, ou registrar oficialmente que aquela versao nao possui artifacts de release.
8. **v1.6.7-final-qa**: Versao de QA final da linha v1.6.x. Gerar client ready report consolidado via `scripts/validators/generate-client-ready-report.sh` e validar com `scripts/validators/validate-client-ready-report.sh`. Documentar status final e recomendacao para transicao para v1.7.0-local-ai-appliance.

---

*Ultima atualizacao: 2026-05-12T12:58:00*
*Auditado por: scripts/validators/audit-v1.6-release-line.sh*

## Restore & Rollback Validation

A validacao de restore e rollback (`scripts/validators/validate-real-restore-rollback-local.sh`)
verifica o fluxo completo de backup, upgrade, restore e rollback em ambiente controlado.

- **Script:** `scripts/validators/validate-real-restore-rollback-local.sh`
- **Testes:** `tests/test_real_restore_rollback_validator.py`, `tests/test_real_restore_rollback_safety.py`, `tests/test_real_restore_rollback_report.py`
- **Saida:** `artifacts/restore-rollback-test/<timestamp>/`
- **Modos:** `--dry-run` (padrao, seguro) ou `--yes` (executa backup, upgrade e rollback reais)

## Commercial Demo E2E Validation

A validacao E2E da demo comercial (`scripts/validators/validate-commercial-demo-e2e-local.sh`)
valida o fluxo completo da demonstracao: seed, meeting-ready, APIs, CRM, propostas,
orcamentos, SOW, relatorios e billing.

- **Script:** `scripts/validators/validate-commercial-demo-e2e-local.sh`
- **Testes:** `tests/test_commercial_demo_e2e_validator.py`, `tests/test_commercial_demo_e2e_report.py`, `tests/test_commercial_demo_e2e_security.py`
- **Saida:** `artifacts/final-qa/commercial-demo-e2e/<timestamp>/`
- **Status:** `DEMO_READY`, `DEMO_READY_WITH_WARNINGS` ou `DEMO_FAILED`

## Clean Install Validation

A validacao de instalacao limpa (`scripts/validators/validate-clean-install-local.sh`) permite simular
uma instalacao do zero em ambiente sandbox, sem risco ao repositorio real.

- **Script:** `scripts/validators/validate-clean-install-local.sh`
- **Validator:** `scripts/validators/validate-clean-install-validator.sh`
- **Testes:** `tests/test_clean_install_validator.py`, `tests/test_clean_install_safety.py`, `tests/test_clean_install_report.py`
- **Saida:** `artifacts/clean-install-test/<timestamp>/`
- **Modos:** `--dry-run` (padrao, seguro) ou `--yes` (executa instalacao real na sandbox)

## Client Ready Final Report

O relatorio final consolidado de pronto para cliente reune todos os artifacts
de validacao em um unico documento versionavel.

- **Gerador:** `scripts/validators/generate-client-ready-report.sh`
- **Validador:** `scripts/validators/validate-client-ready-report.sh`
- **Testes:** `tests/test_client_ready_report.py`, `tests/test_client_ready_report_security.py`, `tests/test_client_ready_report_status.py`
- **Artifacts:** `artifacts/final-qa/client-ready/<timestamp>/`
- **Documento versionavel:** `docs/CLIENT_READY_FINAL_REPORT.md`
- **Status possiveis:** `CLIENT_READY`, `CLIENT_READY_WITH_WARNINGS`, `NOT_READY`
