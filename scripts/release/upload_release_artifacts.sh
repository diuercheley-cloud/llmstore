#!/bin/bash
# scripts/release/upload_release_artifacts.sh
# Script para subir artefatos de release para o GitHub Releases usando gh CLI.

set -e

TAG=$1
ARTIFACTS_DIR=$2

if [ -z "$TAG" ] || [ -z "$ARTIFACTS_DIR" ]; then
    echo "Uso: $0 <tag> <diretorio_de_artefatos>"
    exit 1
fi

if [ ! -d "$ARTIFACTS_DIR" ]; then
    echo "Erro: Diretorio $ARTIFACTS_DIR nao encontrado."
    exit 1
fi

echo "Iniciando upload de artefatos para a tag $TAG..."

# Verifica se a tag existe no repositório remoto (opcional, assume-se que sim no CI)
# gh release view "$TAG" > /dev/null 2>&1 || (echo "Criando release para a tag $TAG..." && gh release create "$TAG" --generate-notes)

# Itera sobre os arquivos no diretório de artefatos
find "$ARTIFACTS_DIR" -maxdepth 1 -type f | while read -r file; do
    echo "Subindo $file..."
    gh release upload "$TAG" "$file" --clobber
done

echo "Upload concluido com sucesso para a tag $TAG."
