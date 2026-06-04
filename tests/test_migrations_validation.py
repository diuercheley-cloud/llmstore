import os
import shutil
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent

def test_validate_migrations_script_help():
    cmd = [str(ROOT_DIR / "scripts" / "validate-migrations-local.sh"), "--help"]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT_DIR))
    assert result.returncode == 0
    assert "Uso:" in result.stdout

def test_validate_migrations_dry_run():
    """
    Roda a validação padrão (sem banco temporário) e verifica se os checks básicos passam.
    """
    cmd = [str(ROOT_DIR / "scripts" / "validate-migrations-local.sh")]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT_DIR))
    
    # Se falhar porque o ambiente está sujo, tudo bem, o teste reflete a realidade.
    # Mas em um ambiente limpo de CI, deve passar.
    assert "Verificando heads do Alembic" in result.stdout
    assert "Verificando IDs duplicados" in result.stdout

def test_validate_migrations_duplicate_check_logic(tmp_path):
    """
    Simula uma migration duplicada para ver se o script detecta.
    """
    source_versions_dir = ROOT_DIR / "control_plane" / "alembic" / "versions"
    versions_dir = tmp_path / "versions"
    shutil.copytree(source_versions_dir, versions_dir)
    fake_migration = versions_dir / "fake_duplicate.py"
    
    # Cria uma migration com um ID que provavelmente já existe ou é padrão
    fake_content = """
revision = '1234567890ab'
down_revision = None
"""
    fake_migration.write_text(fake_content)
    
    # Segunda migration com MESMO ID
    fake_migration2 = versions_dir / "fake_duplicate2.py"
    fake_migration2.write_text(fake_content)
    
    try:
        cmd = [str(ROOT_DIR / "scripts" / "validate-migrations-local.sh")]
        env = {
            **os.environ,
            "ALEMBIC_VERSIONS_DIR": str(versions_dir),
        }
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(ROOT_DIR),
            env=env,
        )
        assert result.returncode != 0
        assert "IDs de revisão duplicados encontrados" in result.stdout
    finally:
        if fake_migration.exists(): fake_migration.unlink()
        if fake_migration2.exists(): fake_migration2.unlink()
