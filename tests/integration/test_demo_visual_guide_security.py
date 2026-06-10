import os
import re

BASE_DIR = "docs/demo-visual-guide"
PLACEHOLDER_DIR = f"{BASE_DIR}/placeholders"

SECRET_PATTERNS = [
    re.compile(r'sk-[a-zA-Z0-9]{20,}'),
    re.compile(r'ADMIN_TOKEN=[a-zA-Z0-9._-]{12,}'),
    re.compile(r'ghp_[a-zA-Z0-9]{36}'),
    re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----'),
]


def test_no_real_secrets_in_guide_files():
    for root, _dirs, files in os.walk(BASE_DIR):
        for fname in files:
            if not fname.endswith('.md') and not fname.endswith('.svg'):
                continue
            path = os.path.join(root, fname)
            with open(path) as f:
                content = f.read()
            for pattern in SECRET_PATTERNS:
                matches = pattern.findall(content)
                for match in matches:
                    if not _is_safe_pattern(match):
                        assert False, (
                            f"Possivel secret encontrado em {path}: {match[:20]}..."
                        )


def _is_safe_pattern(value: str) -> bool:
    safe_prefixes = ['sk-demo-', 'sk-local-', 'sk-example', 'admin-token-123']
    for prefix in safe_prefixes:
        if value.startswith(prefix):
            return True
    return False


def test_psp_pix_limitation_stated():
    """
    Validacao critica: o guia visual deve mencionar que PSP/PIX real nao esta
    disponivel nesta versao local.
    """
    files_to_check = [
        f"{BASE_DIR}/README.md",
        f"{BASE_DIR}/SCREENSHOT_CHECKLIST.md",
        f"{BASE_DIR}/DEMO_STORYBOARD.md",
    ]
    found = False
    for fpath in files_to_check:
        if not os.path.isfile(fpath):
            continue
        with open(fpath) as f:
            content = f.read().lower()
        if 'psp' in content or 'pix' in content or 'manual' in content:
            found = True
            break
    assert found, (
        "Nenhum dos arquivos do guia visual menciona limitacao PSP/PIX. "
        "Adicione uma nota explicita sobre billing manual/local."
    )


def test_placeholders_no_sensitive_data():
    for fname in os.listdir(PLACEHOLDER_DIR):
        if not fname.endswith('.svg') and not fname.endswith('.md'):
            continue
        path = os.path.join(PLACEHOLDER_DIR, fname)
        with open(path) as f:
            content = f.read().lower()
        for sensitive_term in ['real client', 'patient_name', 'true_tax_id']:
            assert sensitive_term not in content, (
                f"Termo sensivel '{sensitive_term}' encontrado em {path}"
            )


def test_placeholders_mark_fictional_data():
    for fname in os.listdir(PLACEHOLDER_DIR):
        if not fname.endswith('.svg'):
            continue
        path = os.path.join(PLACEHOLDER_DIR, fname)
        with open(path) as f:
            content = f.read().lower()
        assert 'ficticio' in content or 'placeholder' in content, (
            f"Placeholder {path} deve indicar que contem dados ficticios"
        )


def test_no_api_key_or_token_in_capture_commands():
    """
    CAPTURE_COMMANDS.md deve usar ${API_KEY} e ${ADMIN_TOKEN} como
    placeholders, nunca valores literais reais.
    """
    path = f"{BASE_DIR}/CAPTURE_COMMANDS.md"
    if not os.path.isfile(path):
        return  # Skip, not required for all configs
    with open(path) as f:
        content = f.read()
    # Should use variable references, not hardcoded keys
    assert '${API_KEY}' in content or 'sk-demo' in content.lower() or 'Bearer ${' in content, (
        "CAPTURE_COMMANDS.md deve usar variaveis de ambiente para tokens/keys"
    )
    # Check if any real-looking key is hardcoded
    real_key_pattern = re.compile(r'[^$]sk-[a-zA-Z0-9]{30,}')
    matches = real_key_pattern.findall(content)
    assert len(matches) == 0, f"Possiveis keys hardcoded em CAPTURE_COMMANDS.md: {matches[:3]}"


def test_demo_storyboard_no_absolute_paths():
    path = f"{BASE_DIR}/DEMO_STORYBOARD.md"
    if not os.path.isfile(path):
        return
    with open(path) as f:
        for i, line in enumerate(f, 1):
            # Avoid false positives for markdown paths
            if '/home/' in line and 'http' not in line:
                assert False, (
                    f"Caminho absoluto encontrado em {path}:{i}: {line.strip()}"
                )


def test_security_report_not_exposing_tokens():
    """
    O storyboard nao deve mencionar tokens reais como exemplos de comando.
    """
    path = f"{BASE_DIR}/DEMO_STORYBOARD.md"
    if not os.path.isfile(path):
        return
    with open(path) as f:
        content = f.read()
    # Check that admin token references use placeholders
    lines = content.split('\n')
    for i, line in enumerate(lines, 1):
        if 'ADMIN_TOKEN' in line and '${ADMIN_TOKEN}' not in line and 'ADMIN_TOKEN' != line.strip():
            if not any(safe in line for safe in ['ADMIN_TOKEN.', 'ADMIN_TOKEN_', 'nao deve', 'nunca deve', 'não deve']):
                assert False, (
                    f"Linha {i}: ADMIN_TOKEN deve usar placeholder: {line.strip()}"
                )


def test_no_real_urls_with_credentials():
    """
    Verifica se nao ha URLs com credenciais nos documentos do guia visual.
    """
    for root, _dirs, files in os.walk(BASE_DIR):
        for fname in files:
            if not fname.endswith('.md'):
                continue
            path = os.path.join(root, fname)
            with open(path) as f:
                for i, line in enumerate(f, 1):
                    url_with_creds = re.search(r'https?://[^:]+:[^@]+@', line)
                    if url_with_creds:
                        assert False, (
                            f"URL com credenciais em {path}:{i}: {line.strip()[:80]}"
                        )
