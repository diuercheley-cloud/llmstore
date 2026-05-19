import pytest
import subprocess
import os
import glob
import shutil

def test_security_report_flow():
    # Garantir que o diretório de artifacts existe para não falhar por isso
    os.makedirs("artifacts/security-reports", exist_ok=True)

    # 1. Executar scripts/check-secrets.sh --all
    # Este script deve rodar e encontrar apenas segredos fake autorizados
    result = subprocess.run(["./scripts/check-secrets.sh", "--all"], capture_output=True, text=True)
    assert result.returncode == 0, f"check-secrets failed: {result.stdout}"
    
    # 2. Executar scripts/security-report-local.sh
    # Rodamos apontando para uma URL dummy para focar nos checks de arquivos locais
    # e validamos que as fixtures fake não causam falha crítica (FAIL)
    result = subprocess.run(
        ["./scripts/security-report-local.sh", "--base-url", "http://localhost:invalid", "--skip-artifacts-scan"], 
        capture_output=True, 
        text=True
    )
    
    # O script retorna 0 se o score for PASS ou PASS_WITH_WARNINGS
    assert result.returncode == 0, f"security-report failed with output: {result.stdout}"
    
    # 3. Validar que o relatório foi gerado
    report_files = glob.glob("artifacts/security-reports/*/security-report.json")
    assert len(report_files) > 0, "Security report JSON not found"
    
    latest_report = max(report_files, key=os.path.getmtime)
    with open(latest_report, 'r') as f:
        import json
        data = json.load(f)
        # O score não deve ser FAIL
        assert data["score"] in ["PASS", "PASS_WITH_WARNINGS"]
        
        # Verificar se as fixtures fake foram classificadas corretamente
        fixtures_checks = [c for c in data["checks"] if "fixture" in c["id"] or "fixture" in c["title"].lower()]
        for check in fixtures_checks:
            assert check["status"] in ["pass", "skip", "warn"]
