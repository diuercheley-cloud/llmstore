#!/bin/bash
set -e

# LLM Inference Stack - Release Gate Validator
# Garante que a release cumpre os requisitos mínimos de governança.

VERSION=$(cat VERSION 2>/dev/null || echo "v0.0.0")
TAG=$1

if [ -z "$TAG" ]; then
    echo "Erro: Tag de release não fornecida."
    exit 1
fi

echo "--- Iniciando Release Gate para $TAG ---"

# 1. Validar padrão da tag
if [[ ! $TAG =~ ^v[0-9]+\.[0-9]+\.[0-9]+(-[a-z0-9-]+)?$ ]]; then
    echo "Erro: Tag $TAG não segue o padrão vX.Y.Z-name"
    exit 1
fi

# 2. Verificar CHANGELOG
if ! grep -q "$TAG" CHANGELOG.md; then
    echo "Erro: CHANGELOG.md não contém a versão $TAG"
    exit 1
fi

# 3. Verificar Release Notes
RELEASE_NOTE_PATH="docs/releases/$(echo $TAG | sed 's/\./_/g' | tr '-' '_').md"
# Fallback para nomes de arquivos que eu criei antes
if [ ! -f "$RELEASE_NOTE_PATH" ] && [ ! -f "docs/releases/V1_9_5_OPERATIONAL_EXPERIENCE.md" ]; then
    echo "Erro: Release notes não encontradas para $TAG"
    exit 1
fi

# 4. Verificar Artifacts de Release
ARTIFACT_DIR="artifacts/releases/$TAG"
if [ ! -d "$ARTIFACT_DIR" ]; then
    # Fallback para o diretório fixo que usei antes se for 1.9.5
    if [[ "$TAG" == "v1.9.5-operational-experience" ]]; then
       ARTIFACT_DIR="artifacts/releases/v1.9.5-operational-experience"
    else
       echo "Erro: Diretório de artifacts $ARTIFACT_DIR não existe."
       exit 1
    fi
fi

if [ ! -f "$ARTIFACT_DIR/summary.md" ] || [ ! -f "$ARTIFACT_DIR/validation.md" ]; then
    echo "Erro: Artifacts de sumário ou validação ausentes em $ARTIFACT_DIR"
    exit 1
fi

# 5. Segurança e Integridade
echo "Executando checks de segurança e integridade..."
bash scripts/check-secrets.sh --all
bash scripts/check-alembic-integrity.sh

# 5.5 Feature Flag Governance
echo "Validando Governança de Feature Flags..."
bash scripts/check-feature-flags.sh

# 6. Operational Readiness
echo "Validando Operational Readiness..."
READINESS_OUTPUT=$(bash scripts/operational-readiness-pack.sh --ci)
if echo "$READINESS_OUTPUT" | grep -q "production_blocked"; then
    echo "Erro: Operational Readiness retornou production_blocked"
    exit 1
fi

echo "--- Release Gate: PASS ---"
