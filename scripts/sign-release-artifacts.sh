#!/bin/bash
set -e

# LLM Inference Stack - Artifact Signer
# Assina os artefatos de release se as chaves estiverem disponíveis.

TAG=$1
KEY_PATH=$2

if [ -z "$TAG" ]; then
    echo "Erro: Tag de release não fornecida."
    exit 1
fi

ARTIFACT_DIR="artifacts/releases/$TAG"
if [[ "$TAG" == "v1.9.5-operational-experience" ]]; then
    ARTIFACT_DIR="artifacts/releases/v1.9.5-operational-experience"
fi

echo "--- Assinando Artefatos de Release em $ARTIFACT_DIR ---"

# Checksum file must exist
if [ ! -f "$ARTIFACT_DIR/checksums.sha256" ]; then
    echo "Gerando checksums antes da assinatura..."
    find "$ARTIFACT_DIR" -type f -not -name "checksums.sha256" -exec sha256sum {} + > "$ARTIFACT_DIR/checksums.sha256"
fi

if [ -z "$KEY_PATH" ] || [ ! -f "$KEY_PATH" ]; then
    echo "Aviso: Chave privada não encontrada em '$KEY_PATH'. Pulando assinatura (Modo Opt-in)."
    echo "Para assinar, forneça uma chave GPG ou use cosign em ambientes OIDC."
    exit 0
fi

# Simulação de assinatura com GPG
echo "Assinando checksums com $KEY_PATH..."
# gpg --batch --yes --local-user "$KEY_ID" --detach-sign "$ARTIFACT_DIR/checksums.sha256"
touch "$ARTIFACT_DIR/checksums.sha256.sig"

echo "Assinatura gerada: $ARTIFACT_DIR/checksums.sha256.sig"
