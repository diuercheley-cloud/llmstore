#!/usr/bin/env bash
set -euo pipefail

# scripts/validators/check-alembic-integrity.sh
# Valida a integridade do histórico do Alembic:
# - Único head linear
# - Sem IDs duplicados
# - Chain contínua sem branches órfãs
# - Histórico consistente (sem ciclos)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../" && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

PYTHON="${ROOT_DIR}/.venv/bin/python"
if [[ ! -f "${PYTHON}" ]]; then
    PYTHON="python3"
fi

# Navega para control_plane para o alembic.ini resolver caminhos relativos corretamente
cd "${ROOT_DIR}/control_plane"

log_info "Rodando validação de integridade das migrations Alembic..."

# Limpa cache compilado do python para evitar ler migrações deletadas do cache
rm -rf "${ROOT_DIR}/control_plane/alembic/versions/__pycache__"

# 1. Executa o script Python para verificar integridade profunda do grafo do Alembic
if ! "${PYTHON}" -c '
import sys
from pathlib import Path
try:
    from alembic.script import ScriptDirectory
    from alembic.config import Config
except ImportError:
    print("Alembic não está instalado no ambiente python.")
    sys.exit(1)

try:
    config = Config("alembic.ini")
    script = ScriptDirectory.from_config(config)
    
    # 1. Walk revisions (detecta ciclos e inconsistências de grafo)
    revisions = list(script.walk_revisions())
    
    # 2. Verifica se há exatamente 1 head
    heads = script.get_heads()
    if len(heads) == 0:
        print("ERRO: Nenhuma head encontrada.")
        sys.exit(1)
    elif len(heads) > 1:
        print(f"ERRO: Múltiplas heads detectadas no histórico: {heads}")
        sys.exit(1)
        
    # 3. Verifica IDs de revisão duplicados
    # Extrai o revision id de cada revision objeto
    rev_ids = [r.revision for r in revisions]
    if len(rev_ids) != len(set(rev_ids)):
        dups = set([x for x in rev_ids if rev_ids.count(x) > 1])
        print(f"ERRO: IDs de revisão duplicados no histórico: {dups}")
        sys.exit(1)
        
    # 4. Verifica chain contínua e sem branches órfãs
    all_revs = {r.revision for r in revisions}
    for r in revisions:
        if r.down_revision:
            down_revs = r.down_revision if isinstance(r.down_revision, tuple) else (r.down_revision,)
            for dr in down_revs:
                if dr not in all_revs:
                    print(f"ERRO: A revisão {r.revision} aponta para down_revision inexistente/órfã {dr}")
                    sys.exit(1)
                    
    print("Sucesso: Grafo do Alembic consistente. Único head, sem duplicatas, chain contínua.")
    sys.exit(0)
except Exception as e:
    print(f"ERRO: Falha ao validar o histórico do Alembic: {e}")
    sys.exit(1)
' ; then
    log_error "A validação de integridade do Alembic falhou!"
    exit 1
fi

log_info "Validação de integridade concluída com sucesso."
exit 0
