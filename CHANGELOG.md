# Changelog

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
