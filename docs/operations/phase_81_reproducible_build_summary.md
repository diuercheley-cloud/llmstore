---
owner: platform-ops
status: consolidated
---

# Phase 81 Summary

## Arquivos criados/alterados

- `control_plane/app/models/operations/reproducible_builds.py`
- `control_plane/app/services/operations/reproducible_builds/`
- `control_plane/app/api/operations_reproducible_builds_admin.py`
- `control_plane/alembic/versions/phase81_reproducible_build_artifact_verification.py`
- `control_plane/app/static/admin/index.html`
- `control_plane/app/static/portal/index.html`
- `control_plane/app/main.py`
- `control_plane/app/models/__init__.py`
- `control_plane/app/models/operations/__init__.py`
- `docs/phases/phase_81_reproducible_build_artifact_verification.md`
- `docs/operations/reproducible_build_artifact_verification.md`
- `docs/operations/phase_81_reproducible_build_summary.md`
- `scripts/validators/validate_phase_81_reproducible_builds.py`
- `Makefile`
- `tests/integration/operations/test_reproducible_build_*.py`
- `tests/integration/operations/test_artifact_verification.py`
- `tests/integration/operations/test_source_artifact_lineage.py`
- `tests/integration/operations/test_build_environment_policy.py`
- `tests/integration/operations/test_artifact_replay_verifier.py`
- `tests/integration/operations/test_phase_81_validation.py`

## Validações executadas

- `python3 scripts/validators/validate_phase_81_reproducible_builds.py`
- `make validate-phase-81-reproducible-builds`

## Testes executados

- `tests/integration/operations/test_reproducible_build_models.py`
- `tests/integration/operations/test_reproducible_build_hash_utils.py`
- `tests/integration/operations/test_reproducible_build_service.py`
- `tests/integration/operations/test_artifact_verification.py`
- `tests/integration/operations/test_source_artifact_lineage.py`
- `tests/integration/operations/test_build_environment_policy.py`
- `tests/integration/operations/test_artifact_replay_verifier.py`
- `tests/integration/operations/test_reproducible_build_provenance_integration.py`
- `tests/integration/operations/test_reproducible_build_receipts.py`
- `tests/integration/operations/test_reproducible_build_audit_events.py`
- `tests/integration/operations/test_reproducible_build_api.py`
- `tests/integration/operations/test_reproducible_build_dashboard.py`
- `tests/integration/operations/test_phase_81_validation.py`
- resultado final: `23 passed`

## Problemas encontrados e corrigidos

- wording inicial em `provenance_integration.py` acionava a regra estática de claim proibida; a redação foi ajustada para manter a limitação sem acionar a validação.
- replay de artifact foi reduzido a campos persistidos para garantir replay determinístico após round-trip no banco.
- validação de manifest foi corrigida para suportar payload `dict` e instância SQLAlchemy sem acesso frágil.

## Limitações conhecidas

- deterministic verification only
- sem compilação real externa
- sem assinatura real
- sem reproducibility certification formal

## Confirmações

- deterministic verification only
- offline-first
- replay verification
- lineage verification
- tenant isolation
- ausência de build externo real
- ausência de dependency resolver externo
