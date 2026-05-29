---
owner: platform-ops
status: consolidated
---

# SECURITY_ARTIFACTS_CLEANUP_v1.5.5

- status: closed
- objetivo: Corrigir a origem dos tokens/secrets em artifacts gerados, aplicando redaction antes da gravação dos arquivos summary/report/log/manifest, e fornecer ferramentas para limpeza segura de artifacts antigos.

## Implementação Realizada

1. **Centralização da Lógica de Redaction**:
   - Criado `lib/redaction.sh` para redação em fluxos de shell.
   - Criado `scripts/redact_json.py` para redação segura em arquivos JSON sem quebrar a estrutura.

2. **Integração nos Geradores de Artifacts**:
   - `scripts/validate-local-production-full.sh`: Agora usa o script centralizado para redigir o diretório de saída.
   - `scripts/release-local-production.sh`: Aplica redação em todos os arquivos da release antes de finalizar.
   - `scripts/security-report-local.sh`: Redige o relatório gerado.
   - `scripts/production-readiness-local.sh`: Redige o relatório de prontidão.
   - `scripts/demo-full-local.sh`: Redige os logs e sumários da demo.

3. **Melhoria do Utilitário de Limpeza/Redação**:
   - `scripts/redact-local-sensitive-artifacts.sh`: Atualizado para processar arquivos `.md`, `.json`, `.log`, `.txt` em vez de apenas deletar diretórios. Suporta `--path`, `--in-place` e `--dry-run`.
   - `scripts/clean-sensitive-artifacts-local.sh`: Novo script robusto para limpeza e redação de artifacts antigos baseada em seções, tempo de vida e retenção. Protege arquivos versionados e arquivos tracked pelo Git.

4. **Validação**:
   - Criado `tests/test_artifact_redaction_source.py` para testes automatizados de regressão.
   - Criado `scripts/validate-artifact-redaction-local.sh` para validação e2e do sistema de redação.
   - `scripts/validate-clean-sensitive-artifacts-local.sh` para validar o novo script de limpeza.
   - `tests/test_clean_sensitive_artifacts.py` para testes unitários/integração do script de limpeza.
   - `scripts/validate-release-artifacts-security.sh`: Novo script para validar que releases não contêm segredos, tarballs versionados ou logs.
   - `tests/test_release_summaries_no_tokens.py`: Testes automatizados para o validador de releases.

   ## Proteção de Releases

   Releases agora possuem uma camada extra de proteção:
   - **Manifestos e Sumários Protegidos**: `summary.json`, `summary.md`, `release-manifest.json` e `bundle-manifest.json` são validados contra tokens e segredos (`sk-`, `ADMIN_TOKEN`, `Bearer`, etc.).
   - **Bloqueio de Tarballs Versionados**: O validador garante que nenhum arquivo `.tar.gz` seja versionado ou staged por engano.
   - **Validação de Checksums**: `bundle-checksums.sha256` é validado para garantir integridade e que apenas nomes de arquivos permitidos sejam listados.
   - **Integração no Pipeline**: A release falha automaticamente se qualquer segredo for detectado após a redação.

5. **Melhoria no Scoring do Relatório de Segurança**:
   - `scripts/security-report-local.sh`: Refatorado para separar scans por categorias (versionable, staged, releases versionadas, releases não-trackeadas, artifacts ignorados).
   - **Lógica de Severidade Inteligente**: Secrets em arquivos trackeados ou staged geram `FAIL`. Secrets em artifacts ignorados geram `WARN`.
   - **Suporte a Redaction**: Tokens que contêm marcadores de redação (ex: `***REDACTED***`, `***masked***`) são classificados como `redacted_safe` e não geram warning nem impactam o score.
   - **Categorização no Relatório**: O relatório MD agora separa achados em "Blocking", "Warnings" e "Informational & Redacted".
   - **Compatibilidade**: Mantidos IDs de checks legados para não quebrar integrações existentes.

## Resultados

- O `security-report-local.sh` não deve mais detectar segredos em artifacts gerados, pois eles são limpos na origem.
- O score de segurança deve retornar a `PASS` sem warnings de `generated_artifact`.
- Ferramentas automáticas permitem manter o diretório `artifacts/` limpo e seguro sem intervenção manual arriscada.

## Validação Final da Release

- `2026-05-09`: `./scripts/security-report-local.sh` retornou `PASS`.
- Totais do relatório: `pass=23`, `warn=0`, `fail=0`, `skip=64`, `critical_failures=0`, `high_failures=0`.
- `./scripts/check-secrets.sh --all`, `./scripts/diagnose-artifact-secrets.sh`, `./scripts/validate-artifact-redaction-local.sh`, `./scripts/validate-clean-sensitive-artifacts-local.sh` e `./scripts/validate-release-artifacts-security.sh` passaram.
- `./scripts/validate-local-production-full.sh`, `./scripts/demo-full-local.sh --no-build` e `./scripts/release-local-production.sh --version v1.5.5-security-artifacts-clean --allow-dirty` concluíram com sucesso.
- O bundle `.tar.gz` foi gerado apenas para validação local e removido em seguida para não ser versionado.
