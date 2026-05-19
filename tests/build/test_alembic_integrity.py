import subprocess
from pathlib import Path

def test_alembic_integrity_script():
    # Encontra o diretório raiz do projeto
    project_dir = Path(__file__).resolve().parents[2]
    script_path = project_dir / "scripts" / "check-alembic-integrity.sh"
    
    res = subprocess.run(["bash", str(script_path)], capture_output=True, text=True, cwd=str(project_dir))
    
    assert res.returncode == 0
    assert "Grafo do Alembic consistente" in res.stdout or "Validação de integridade concluída com sucesso" in res.stdout
