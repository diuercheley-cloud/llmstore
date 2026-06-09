import subprocess
import os
import datetime
import sys
from docx import Document

def run_all_tests():
    # Define o diretório de testes
    test_dir = "tests"
    
    # Define PYTHONPATH para que o pytest encontre os módulos na pasta scripts/
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd(); env["ADMIN_TOKEN"] = "917b7930cac1eeabff1496a0604249e9216cd8e15281b97657e155593b219f69"
    env["PYTHONUNBUFFERED"] = "1"
    
    # Executa todos os testes com saída unbuffered para manter o streaming por teste.
    cmd = [sys.executable, "-u", "-m", "pytest", test_dir, "-v", "--tb=short"]
    print(f"Executando: {' '.join(cmd)}")
    print(f"PYTHONPATH: {env['PYTHONPATH']}")
    
    process = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    stdout_lines = []

    # Lê a saída em tempo real, linha a linha.
    for line in process.stdout:
        print(line, end="")
        stdout_lines.append(line)

    return process.wait(), "".join(stdout_lines), ""

def generate_report(test_exit_code, stdout, stderr):
    doc = Document()
    doc.add_heading('Relatório de Execução de Testes', 0)
    
    doc.add_paragraph(f'Data da execução: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    
    status = "SUCESSO" if test_exit_code == 0 else "FALHA"
    paragraph = doc.add_paragraph(f'Status Final: ')
    paragraph.add_run(status).bold = True
    
    doc.add_paragraph(f'Código de saída do Pytest: {test_exit_code}')
    
    if test_exit_code != 0:
        doc.add_heading('Detalhes das Falhas', level=1)
        doc.add_paragraph(stdout[-20000:]) # Limitando para não exceder tamanho do docx
        if stderr:
            doc.add_paragraph('Erros adicionais:')
            doc.add_paragraph(stderr[-5000:])
    
    report_name = f'relatorio_testes_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.docx'
    doc.save(report_name)
    return report_name

if __name__ == "__main__":
    print("Iniciando a execução de todos os testes...")
    exit_code, stdout, stderr = run_all_tests()
    
    print("\nGerando relatório...")
    report_path = generate_report(exit_code, stdout, stderr)
    print(f"Relatório gerado com sucesso: {report_path}")
