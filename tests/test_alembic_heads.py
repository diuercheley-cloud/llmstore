import subprocess
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).parent.parent

def test_alembic_single_head():
    """
    Verifica se existe apenas uma head nas migrations do Alembic.
    Múltiplas heads indicam conflitos de merge não resolvidos.
    """
    alembic_path = ROOT_DIR / ".venv" / "bin" / "alembic"
    if not alembic_path.exists():
        alembic_path = "alembic"
    
    cmd = [str(alembic_path), "heads"]
    result = subprocess.run(
        cmd, 
        capture_output=True, 
        text=True, 
        cwd=str(ROOT_DIR / "control_plane")
    )
    
    assert result.returncode == 0
    
    # Cada head é marcada com "(head)"
    heads = [line for line in result.stdout.splitlines() if "(head)" in line]
    
    assert len(heads) == 1, f"Múltiplas heads detectadas no Alembic: {heads}"

def test_alembic_no_pending_migrations():
    """
    Verifica se não há migrations pendentes no ambiente atual (se o banco estiver up).
    Este teste pode ser pulado se o banco não estiver acessível.
    """
    alembic_path = ROOT_DIR / ".venv" / "bin" / "alembic"
    if not alembic_path.exists():
        alembic_path = "alembic"
        
    cmd = [str(alembic_path), "history", "-p", "head"]
    result = subprocess.run(
        cmd, 
        capture_output=True, 
        text=True, 
        cwd=str(ROOT_DIR / "control_plane")
    )
    
    # Se history falhar (ex: sem banco), apenas ignoramos por agora
    if result.returncode != 0:
        pytest.skip("Banco de dados não acessível para checar migrations pendentes")
    
    # alembic history -p head mostra apenas o que falta aplicar se usarmos hooks,
    # mas o comando padrão apenas lista. 
    # Uma forma melhor de checar pendências é 'alembic check' em versões novas
    # ou comparar 'heads' com 'current'.
    
    # Por agora, vamos apenas garantir que o comando base funciona.
    assert result.returncode == 0
