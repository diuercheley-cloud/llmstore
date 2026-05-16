# Reproducible Build & Artifact Verification Framework

## Overview

O framework da Phase 81 trata manifests de build reproduzível e artifacts associados ao runtime de plugins/extensions e federation artifacts. O foco é auditabilidade determinística e offline-first.

## Reproducible Build Manifests

- `ReproducibleBuildManifest` registra nome, escopo, referência de source, versão determinística, hash do ambiente e hash lógico do manifest.
- `replay_safe=True` é obrigatório.
- Timestamps não entram no hash lógico.

## Artifact Verification

- `ArtifactVerificationRecord` usa SHA-256 determinístico.
- mismatch de hash resulta em `blocked`.
- replay verification é obrigatório.
- No real external build execution.

## Source-to-Artifact Lineage

- `SourceArtifactLineage` preserva source hash, artifact hash e lineage hash.
- lineage conflict bloqueia a validação.
- lineage replay-verifiable apenas.

## Build Environment Constraints

- `BuildEnvironmentConstraint` impõe `offline_only=True` e `required_determinism=True` por padrão.
- `external_network_allowed=True` é bloqueado.
- `external_dependency_resolution_allowed=True` é bloqueado.
- dynamic dependency install, shell installer e remote package manager são proibidos.

## Replay Verification

- `ArtifactReplayVerifier` reexecuta o cálculo lógico de hashes para manifest, artifact e lineage.
- deterministic verification only.
- sem random, subprocess arbitrário ou rede.

## Provenance / SBOM Integration

- integração conceitual com a Phase 80
- placeholder alignment com provenance/SBOM
- sem dependency resolver externo
- sem assinatura real

## Receipts

Os receipts incluem:

- `receipt_type`
- `client_id`
- `subject_id`
- `immutable_hash`
- `payload_hash`
- `deterministic_version`
- `signature_placeholder`
- `generated_at`

## Audit Events

Eventos suportados:

- `reproducible_build_manifest_created`
- `artifact_verified`
- `lineage_verified`
- `replay_verification_completed`
- `build_environment_validated`
- `reproducibility_verification_completed`
- `reproducible_build_receipt_created`

## API Admin

Endpoints administrativos:

- `POST /admin/operations/reproducible-builds/manifests`
- `GET /admin/operations/reproducible-builds/manifests`
- `GET /admin/operations/reproducible-builds/manifests/{manifest_id}`
- `POST /admin/operations/reproducible-builds/manifests/{manifest_id}/verify`
- `POST /admin/operations/reproducible-builds/artifacts/verify`
- `POST /admin/operations/reproducible-builds/lineage/verify`
- `POST /admin/operations/reproducible-builds/replay/verify`
- `POST /admin/operations/reproducible-builds/environment/validate`
- `POST /admin/operations/reproducible-builds/manifests/{manifest_id}/receipt`

Tenant isolation é obrigatório. Payload sensível não é exposto.

## Dashboard

A seção “Reproducible Build & Artifact Verification Framework” mostra:

- total de manifests
- manifests reproducible/warning/blocked
- artifact verification status
- replay verification status
- lineage verification status
- build environment validation
- replay_safe status
- receipts disponíveis

## Offline Compatibility

- offline-first reproducible build framework
- sem chamadas externas
- sem compilação real externa

## Security Notes

- deterministic verification only
- sem plaintext sensível
- sem assinatura real
- sem reproducibility certification formal
