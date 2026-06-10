#!/bin/bash
set -e

# LLM Inference Stack - Artifact Governance Verifier
# Garante que os artefatos de release estão limpos e íntegros.

TAG=$1
if [ -z "$TAG" ]; then
    echo "Erro: Tag de release não fornecida."
    exit 1
fi

ARTIFACT_DIR="artifacts/releases/$TAG"
if [[ "$TAG" == "v1.9.5-operational-experience" ]]; then
    ARTIFACT_DIR="artifacts/releases/v1.9.5-operational-experience"
fi

echo "--- Verificando Governança de Artefatos em $ARTIFACT_DIR ---"

# 0. Verificar presença de artifacts obrigatórios
REQUIRED_ARTIFACTS=(
    "summary.md"
    "validation.md"
    "agentic-readiness.md"
    "security.md"
    "evals.md"
    "slo.md"
)
MISSING_ARTIFACTS=()
for artifact in "${REQUIRED_ARTIFACTS[@]}"; do
    if [ ! -f "$ARTIFACT_DIR/$artifact" ]; then
        MISSING_ARTIFACTS+=("$artifact")
    fi
done
if [ ${#MISSING_ARTIFACTS[@]} -gt 0 ]; then
    echo "ERRO: Artifacts obrigatórios ausentes:"
    for a in "${MISSING_ARTIFACTS[@]}"; do
        echo "  - $ARTIFACT_DIR/$a"
    done
    exit 1
fi
echo "[PASS] Todos os artifacts obrigatórios presentes."

# 1. Proibir arquivos sensíveis
SENSITIVE_FILES=(
    ".env"
    ".env.local"
    "*.key"
    "data/pki/*"
    "*.pem"
)

for pattern in "${SENSITIVE_FILES[@]}"; do
    FOUND=$(find "$ARTIFACT_DIR" -name "$pattern" -type f)
    if [ -n "$FOUND" ]; then
        echo "ERRO: Arquivo sensível detectado nos artefatos: $FOUND"
        exit 1
    fi
done

# 2. Proibir dados de runtime / caches
BLOAT_PATTERNS=(
    "__pycache__"
    ".pytest_cache"
    "*.bin"
    "models/*"
)
for pattern in "${BLOAT_PATTERNS[@]}"; do
    FOUND=$(find "$ARTIFACT_DIR" -name "$pattern")
    if [ -n "$FOUND" ]; then
        echo "AVISO: Bloat ou cache detectado nos artefatos: $FOUND"
        # Opcional: remover ou falhar. Aqui vamos apenas avisar para simplificar.
    fi
done

# 3. Gerar Checksums
echo "Gerando checksums..."
find "$ARTIFACT_DIR" -type f -not -name "checksums.sha256" -exec sha256sum {} + > "$ARTIFACT_DIR/checksums.sha256"

echo "Checksums gerados em $ARTIFACT_DIR/checksums.sha256"
echo "--- Governança de Artefatos: OK ---"
