#!/usr/bin/env bash
set -euo pipefail

echo "Validating backup before upgrade logic..."

# upgrade --dry-run mostra que backup seria criado
OUT1=$(./scripts/deploy/upgrade-local.sh --to-version HEAD --dry-run 2>&1 || true)
if ! echo "$OUT1" | grep -q "Criando backup de segurança"; then
    echo "Fail: dry-run should show backup creation."
    exit 1
fi

# upgrade sem --skip-backup referencia backup-local.sh
if ! echo "$OUT1" | grep -q "scripts/backup/backup-local.sh"; then
    echo "Fail: dry-run should reference backup-local.sh"
    exit 1
fi

# --skip-backup sem --yes falha
if ./scripts/deploy/upgrade-local.sh --to-version HEAD --skip-backup --dry-run > /dev/null 2>&1; then
    echo "Fail: --skip-backup without --yes should fail"
    exit 1
fi

# --skip-backup --yes registra risco
OUT2=$(./scripts/deploy/upgrade-local.sh --to-version HEAD --skip-backup --yes --dry-run 2>&1 || true)
if ! echo "$OUT2" | grep -q "Pular backup foi solicitado e confirmado"; then
    echo "Fail: --skip-backup --yes should log risk."
    exit 1
fi

# rollback aceita backup-id
OUT3=$(./scripts/dev/rollback-local.sh --to-version HEAD --backup-id mybackup --yes --dry-run 2>&1 || true)
if ! echo "$OUT3" | grep -q "Restaurando backup a partir de: mybackup"; then
    echo "Fail: rollback should accept backup id."
    exit 1
fi

echo "Validation passed."
