import re
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
LIB_PATH = ROOT_DIR / "scripts" / "lib" / "operator-errors.sh"

def strip_ansi(text):
    return re.sub(r'\x1b\[[0-9;]*m', '', text)

def run_bash_func(func_call):
    cmd = f"source {LIB_PATH} && {func_call}"
    res = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True)
    res.stdout = strip_ansi(res.stdout)
    return res

def test_operator_error_format():
    res = run_bash_func('operator_error "CODE" "Message" "Remediation" "Details"')
    assert "[ERROR] Código: CODE" in res.stdout
    assert "O que aconteceu:\nMessage" in res.stdout
    assert "Como resolver:\nRemediation" in res.stdout
    assert "Detalhe técnico:\nDetails" in res.stdout

def test_operator_warning_format():
    res = run_bash_func('operator_warning "CODE" "Message" "Remediation" "Details"')
    assert "[WARNING] Código: CODE" in res.stdout
    assert "O que aconteceu:\nMessage" in res.stdout
    assert "Como resolver:\nRemediation" in res.stdout
    assert "Detalhe técnico:\nDetails" in res.stdout

def test_operator_success_format():
    res = run_bash_func('operator_success "Success message"')
    assert "[SUCCESS] Success message" in res.stdout

def test_next_steps():
    res = run_bash_func('add_next_step "Step 1" && add_next_step "Step 2" && print_next_steps')
    assert "Próximos passos:" in res.stdout
    assert "- Step 1" in res.stdout
    assert "- Step 2" in res.stdout
