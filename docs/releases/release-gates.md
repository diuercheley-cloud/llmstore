# Release Gates

Os **Release Gates** são as barreiras de qualidade finais que garantem que uma versão do `llm-inference-stack` está pronta para ser promovida para produção.

## Critérios de Passagem

Para que uma release seja aprovada pelo gate (`make release-gate`), ela deve cumprir:

1.  **Metadados**:
    *   Tag segue o padrão `vX.Y.Z-name`.
    *   `CHANGELOG.md` contém a versão e notas de mudança.
    *   `docs/releases/` contém o documento de release notes detalhado.

2.  **Validação Técnica**:
    *   `make validate-quick` deve passar 100%.
    *   `make security` deve gerar relatório sem vulnerabilidades críticas.
    *   `make operational-readiness` não pode retornar o estado `production_blocked`.

3.  **Segurança**:
    *   Escaneamento de segredos (`check-secrets.sh`) deve estar limpo.
    *   Integridade de migrações (`check-alembic-integrity.sh`) deve ser validada.

## Falha no Gate
Se qualquer um dos critérios falhar, a pipeline de release será interrompida imediatamente, impedindo a publicação de artefatos instáveis ou inseguros.
