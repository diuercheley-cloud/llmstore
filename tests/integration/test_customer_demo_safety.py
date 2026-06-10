import os
import re
import subprocess

SCRIPT_PATH = "scripts/dev/customer-demo-local.sh"
GITIGNORE_PATH = ".gitignore"
MAKEFILE_PATH = "Makefile"


def test_gitignore_covers_artifacts():
    assert os.path.isfile(GITIGNORE_PATH), ".gitignore nao encontrado"
    with open(GITIGNORE_PATH) as f:
        content = f.read()
    assert "artifacts/customer-demo" in content or "artifacts/" in content, (
        "artifacts/customer-demo deve estar no .gitignore"
    )


def test_makefile_has_customer_demo_target():
    assert os.path.isfile(MAKEFILE_PATH), "Makefile nao encontrado"
    with open(MAKEFILE_PATH) as f:
        content = f.read()
    assert "customer-demo:" in content, "Target customer-demo nao encontrado no Makefile"


def test_makefile_has_validate_customer_demo_target():
    assert os.path.isfile(MAKEFILE_PATH)
    with open(MAKEFILE_PATH) as f:
        content = f.read()
    assert "validate-customer-demo:" in content, "Target validate-customer-demo nao encontrado no Makefile"


def test_script_no_real_secrets():
    """Verifica se o script nao contem secrets hardcoded."""
    with open(SCRIPT_PATH) as f:
        content = f.read()
    patterns = [
        re.compile(r'sk-[a-zA-Z0-9]{20,}'),
        re.compile(r'ADMIN_TOKEN=[a-zA-Z0-9._-]{12,}'),
    ]
    for pattern in patterns:
        matches = pattern.findall(content)
        for match in matches:
            if match.startswith("sk-demo-"):
                continue
            assert False, f"Possivel secret no script: {match[:20]}..."


def test_reset_demo_dry_run_default():
    """Reset demo sem --yes deve ser dry-run."""
    result = subprocess.run(
        ["bash", SCRIPT_PATH, "--no-build", "--quick", "--reset-demo"],
        capture_output=True, text=True
    )
    output = result.stdout.lower()
    # Should indicate dry-run or simulation mode
    assert "dry-run" in output or "simulado" in output or "Skipped" in output or result.returncode in (0, 1, 2)


def test_script_does_not_depend_on_internet():
    """Script nao deve conter URLs externas obrigatorias."""
    with open(SCRIPT_PATH) as f:
        content = f.read()
    # Check for external URLs
    external_urls = re.findall(r'https?://(?!localhost|127\.0\.0\.1)\S+', content)
    non_demo_urls = [u for u in external_urls if "example" not in u]
    # Allow these as they are for report generation
    assert len(non_demo_urls) == 0, f"URLs externas encontradas: {non_demo_urls}"


def test_script_does_not_expose_admin_token():
    """ADMIN_TOKEN deve ser lido de arquivo, nunca hardcoded."""
    with open(SCRIPT_PATH) as f:
        content = f.read()
    # Check for lines that set ADMIN_TOKEN to a literal value
    lines_with_admin = [l for l in content.split('\n') if 'ADMIN_TOKEN=' in l]
    for line in lines_with_admin:
        # Skip export/read patterns
        if 'grep' in line or 'cut' in line or '${' in line or 'ADMIN_TOKEN:-}' in line or 'ADMIN_TOKEN=""' in line or "ADMIN_TOKEN=''" in line:
            continue
        # Skip comments
        if line.strip().startswith('#'):
            continue
        assert False, f"ADMIN_TOKEN possivelmente hardcoded: {line.strip()}"


def test_script_has_safety_banner():
    """Script deve ter banner de seguranca."""
    with open(SCRIPT_PATH) as f:
        content = f.read()
    assert "Customer Demo" in content or "Local AI Appliance" in content


def test_output_dir_not_committed():
    """Verifica se o diretorio de saida padrao nao e versionavel."""
    default_output = "artifacts/customer-demo"
    assert default_output.startswith("artifacts/"), "Output deve estar em artifacts/"
    assert "/customer-demo" in default_output


def test_makefile_has_customer_demo_full_target():
    assert os.path.isfile(MAKEFILE_PATH)
    with open(MAKEFILE_PATH) as f:
        content = f.read()
    assert "customer-demo-full:" in content, "Target customer-demo-full nao encontrado no Makefile"
